import random
from datetime import datetime,timezone,timedelta
from sqlalchemy import select,func
from src.config.database import Session,Base,engine
from src.models.entities import User,Batch,Inspection,Review,Pairing
from src.utils.security import password_hash
from src.services.statistics import diagnose
def seed():
    Base.metadata.create_all(engine);rng=random.Random(3101)
    with Session() as db:
        for role in ['admin','analyst','viewer']:
            email=f'{role}@demo.local'
            if not db.scalar(select(User).where(User.email==email)):db.add(User(email=email,password_hash=password_hash('Demo123!'),role=role))
        db.flush()
        for i in range(40):
            code='QH-1115-A' if i==0 else f'QH-{1101+i:04}-B'
            batch=db.scalar(select(Batch).where(Batch.code==code))
            if not batch:
                batch=Batch(code=code,line=['一线','二线','三线'][i%3],supplier=['丰垦粮业','北原合作社','河谷粮仓'][i%3],tonnes=round(25+i*.7,1),received_date=f'2026-11-{1+i%15:02}')
                db.add(batch);db.flush()
            for j in range(15):
                sc=f'{code}-S{j+1:02}';val=round(max(65,min(82,rng.gauss(73+i%3*1.4,1.6))),2)
                if i in (0,9,25) and j==14:val=65.0 if i==0 else 82.0
                moisture=round(rng.uniform(11.5,14.2),2)
                if not db.scalar(select(Inspection).where(Inspection.sample_code==sc)):
                    db.add(Inspection(sample_code=sc,batch_id=batch.id,flour_yield=val,moisture=moisture,inspector=['林洁','周麦','陈禾'][i%3]))
        db.flush()
        if not db.scalar(select(Review).where(Review.title=='11月15日全线出粉率初审')):
            from src.services.business import inspections
            rows=inspections(db)
            db.add(Review(title='11月15日全线出粉率初审',line='全部',status='completed',snapshot=rows,result=diagnose(rows),created_by='analyst@demo.local',note='待质量负责人核对异常点及签核'))
        db.flush()
        # 调参配对演示：一线在 2026-11-12 08:00 UTC 调整磨辊，前后各 48 小时窗口内带采样时间的样本。
        # 既有 600 条样本保持 sampled_at 为 NULL，作为“旧样本时间未知”的演示。
        adj=random.Random(3102);T=datetime(2026,11,12,8,0,tzinfo=timezone.utc)
        plan=[('QH-ADJ-01','丰垦粮业',6,6,72.0,74.8,(12.2,13.2),(12.2,13.2)),
              ('QH-ADJ-02','北原合作社',3,1,72.0,74.0,(12.4,13.4),(12.4,13.4)),
              ('QH-ADJ-03','河谷粮仓',4,0,72.5,0.0,(12.0,13.0),None),
              ('QH-ADJ-04','丰垦粮业',3,3,72.2,74.4,(12.0,12.6),(14.6,15.2))]
        offs=[-46,-38,-30,-22,-14,-6]
        for code,supplier,n_b,n_a,mean_b,mean_a,moist_b,moist_a in plan:
            batch=db.scalar(select(Batch).where(Batch.code==code))
            if not batch:
                batch=Batch(code=code,line='一线',supplier=supplier,tonnes=26.5,received_date='2026-11-10')
                db.add(batch);db.flush()
            def put(suffix,val,moist,at):
                sc=f'{code}-{suffix}'
                if not db.scalar(select(Inspection).where(Inspection.sample_code==sc)):
                    db.add(Inspection(sample_code=sc,batch_id=batch.id,flour_yield=val,moisture=moist,inspector='林洁',sampled_at=at))
            for k in range(n_b):
                put(f'B{k+1:02}',round(max(65,min(82,adj.gauss(mean_b,0.5))),2),round(adj.uniform(*moist_b),2),T+timedelta(hours=offs[k]))
            for k in range(n_a):
                put(f'A{k+1:02}',round(max(65,min(82,adj.gauss(mean_a,0.5))),2),round(adj.uniform(*moist_a),2),T+timedelta(hours=-offs[k]))
        # 窗口外样本：演示“采样时刻不在时段内”的排除原因
        extra=db.scalar(select(Batch).where(Batch.code=='QH-ADJ-01'))
        for suffix,hours in (('X01',-80),('X02',90)):
            sc=f'QH-ADJ-01-{suffix}'
            if not db.scalar(select(Inspection).where(Inspection.sample_code==sc)):
                db.add(Inspection(sample_code=sc,batch_id=extra.id,flour_yield=73.1,moisture=12.7,inspector='周麦',sampled_at=T+timedelta(hours=hours)))
        db.flush()
        if not db.scalar(select(Pairing).where(Pairing.title=='磨辊调参前后配对（演示）')):
            from src.services.business import line_snapshot
            from src.services.pairing import analyze
            accepted=datetime.now(timezone.utc)
            rows=line_snapshot(db,'一线',accepted)
            db.add(Pairing(title='磨辊调参前后配对（演示）',line='一线',status='completed',adjusted_at=T,window_hours=48,moisture_tolerance=1.0,accepted_at=accepted,snapshot=rows,result=analyze(rows,'一线',T,48,1.0),created_by='analyst@demo.local',note='演示数据：调参前后等长时段同批次配对'))
        db.commit()
        print({m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in [Batch,Inspection,Review,Pairing]})
if __name__=='__main__':seed()
