import hashlib,json
from datetime import datetime,timezone,timedelta
EPS=1e-9
def _parse(v):
    t=v if isinstance(v,datetime) else datetime.fromisoformat(str(v).replace('Z','+00:00'))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
def _iso(t):return t.astimezone(timezone.utc).isoformat()
def _brief(r):
    return {'id':r['id'],'sample_code':r['sample_code'],'batch_code':r['batch_code'],'flour_yield':r['flour_yield'],'moisture':r['moisture'],'sampled_at':r['sampled_at'],'inspector':r.get('inspector','')}
def _mcmf(nb,na,costs):
    """最小费用最大流（单位容量二分图）。costs:{(i,j):整数成本}。
    返回 (最大流量, 该流量下费用最小的匹配 [(i,j)])。
    邻接按固定顺序插入、Bellman-Ford 全量松弛，结果确定可复现。"""
    N=2+nb+na;S=0;T=N-1;INF=float('inf')
    adj=[[] for _ in range(N)]
    def add(u,v,cap,cost):
        adj[u].append([v,cap,cost,len(adj[v])]);adj[v].append([u,0,-cost,len(adj[u])-1])
    for i in range(nb):add(S,1+i,1,0)
    for i,j in sorted(costs):add(1+i,1+nb+j,1,costs[(i,j)])
    for j in range(na):add(1+nb+j,T,1,0)
    flow=0
    while True:
        dist=[INF]*N;prev=[None]*N;dist[S]=0
        for _ in range(N-1):
            moved=False
            for u in range(N):
                if dist[u]==INF:continue
                for ei,e in enumerate(adj[u]):
                    if e[1]>0 and dist[u]+e[2]<dist[e[0]]:
                        dist[e[0]]=dist[u]+e[2];prev[e[0]]=(u,ei);moved=True
            if not moved:break
        if prev[T] is None:break
        v=T
        while v!=S:
            u,ei=prev[v];adj[u][ei][1]-=1;adj[v][adj[u][ei][3]][1]+=1;v=u
        flow+=1
    pairs=[(i,e[0]-(1+nb)) for i in range(nb) for e in adj[1+i] if 1+nb<=e[0]<1+nb+na and e[1]==0]
    return flow,pairs
def _scheme(before,after,pairs_idx):
    pairs=[]
    for i,j in sorted(pairs_idx,key=lambda p:(before[p[0]]['_t'],before[p[0]]['id'],after[p[1]]['id'])):
        b,a=before[i],after[j]
        pairs.append({'before':_brief(b),'after':_brief(a),'delta_yield':round(a['flour_yield']-b['flour_yield'],2),'delta_moisture':round(a['moisture']-b['moisture'],2)})
    total=round(sum(p['delta_yield'] for p in pairs),2)
    return {'pairs':pairs,'total_delta':total,'avg_delta':round(total/len(pairs),4) if pairs else None}
def analyze(snapshot,line,adjusted_at,window_hours,moisture_tolerance):
    """调参前后配对分析。snapshot 为受理时刻冻结的本产线检验记录。
    先求最大配对数，再给出所有最大配对方案中平均增幅的下界与上界及两端明细。"""
    T=_parse(adjusted_at);d=timedelta(hours=window_hours);b_start,a_end=T-d,T+d
    tol=float(moisture_tolerance)
    before,after,excluded=[],[],[]
    for row in sorted(snapshot,key=lambda r:(r['sample_code'],r['id'])):
        t=_parse(row['sampled_at']) if row.get('sampled_at') else None
        brief={k:row.get(k) for k in ('id','sample_code','batch_code','sampled_at')}
        if t is None:
            excluded.append({**brief,'reason':'采样时间未知（旧样本），无法按采样时刻入组'})
        elif b_start<=t<T:
            before.append({**row,'_t':t})
        elif T<=t<a_end:
            after.append({**row,'_t':t})
        else:
            excluded.append({**brief,'reason':f'采样时刻不在调参前后各 {window_hours} 小时等长时段内'})
    before.sort(key=lambda r:(r['_t'],r['id']));after.sort(key=lambda r:(r['_t'],r['id']))
    # 配对约束：同一批次且水分差不超过设定值；成本为增幅（百分点×100 取整，保证确定性）
    deltas={}
    for i,b in enumerate(before):
        for j,a in enumerate(after):
            if b['batch_id']==a['batch_id'] and abs(b['moisture']-a['moisture'])<=tol+EPS:
                deltas[(i,j)]=round((a['flour_yield']-b['flour_yield'])*100)
    k,min_idx=_mcmf(len(before),len(after),dict(deltas))
    _,max_idx=_mcmf(len(before),len(after),{e:-c for e,c in deltas.items()})
    scheme_min=_scheme(before,after,min_idx);scheme_max=_scheme(before,after,max_idx)
    used={before[i]['id'] for i,_ in min_idx+max_idx}|{after[j]['id'] for _,j in min_idx+max_idx}
    unpaired=[]
    for side,rows,other,opp in (('调参前',before,after,'调参后'),('调参后',after,before,'调参前')):
        for r in rows:
            if r['id'] in used:continue
            same=[o for o in other if o['batch_id']==r['batch_id']]
            if not same:reason=f'同批次在{opp}时段无样本'
            elif all(abs(o['moisture']-r['moisture'])>tol+EPS for o in same):reason=f'同批次{opp}样本水分差均超过 ±{tol:g} 个百分点'
            else:reason='同批次可配对样本已用于其他配对（保持最多对数）'
            unpaired.append({**_brief(r),'side':side,'reason':reason})
    return {
        'line':line,'adjusted_at':_iso(T),'window_hours':window_hours,'moisture_tolerance':tol,
        'windows':{'before':{'start':_iso(b_start),'end':_iso(T)},'after':{'start':_iso(T),'end':_iso(a_end)}},
        'counts':{'line_total':len(snapshot),'before':len(before),'after':len(after),'unknown_time':sum(1 for e in excluded if e['sampled_at'] is None),'out_of_window':sum(1 for e in excluded if e['sampled_at'] is not None),'paired':k},
        'pair_count':k,
        'avg_delta_min':scheme_min['avg_delta'],'avg_delta_max':scheme_max['avg_delta'],
        'scheme_min':scheme_min,'scheme_max':scheme_max,
        'unpaired':unpaired,'excluded':excluded,
        'checksum':hashlib.sha256(json.dumps(snapshot,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
        'method':f'配对口径：仅使用受理时已提交、采样时刻落在调参前后各 {window_hours} 小时等长时段内的本产线样本（迟到记录按采样时刻入组，受理后的补录不影响本次快照）；同一批次且水分差不超过 ±{tol:g} 个百分点才可配对，每份样本最多参与一对。先在二分图上求最大配对数，再在所有达到最大配对数的方案中以最小费用最大流取配对平均增幅最小与最大的方案。增幅 = 调参后样本出粉率 − 调参前样本出粉率；配对数为零时上下界为空。未参与样本指在下界与上界两种方案中都未进入配对的样本；达到最多对数时具体占用哪些样本可能因方案而异，两端明细见配对表。'}
