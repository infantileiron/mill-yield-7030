import time,os,traceback,json
from pathlib import Path
from sqlalchemy import select
from src.config.database import Session,Base,engine,ensure_schema
from src.models.entities import Review,Pairing
from src.services.business import queue
from src.services.statistics import diagnose
from src.services.pairing import analyze
Base.metadata.create_all(engine)
ensure_schema()
# Recover committed jobs if a process stopped between database commit and queue push.
with Session() as db:
    for obj in db.scalars(select(Review).where(Review.status.in_(['queued','running']))):queue.rpush('mill:jobs',obj.id)
    for obj in db.scalars(select(Pairing).where(Pairing.status.in_(['queued','running']))):queue.rpush('mill:pairjobs',obj.id)
while True:
    Path('/tmp/worker-heartbeat').touch()
    item=queue.blpop(['mill:jobs','mill:pairjobs'],timeout=2)
    if not item:continue
    key,raw=item[0],int(item[1])
    with Session() as db:
        model=Review if key=='mill:jobs' else Pairing
        obj=db.get(model,raw)
        if not obj or obj.status not in ('queued','running'):continue
        obj.status='running';db.commit()
        try:
            obj.result=diagnose(obj.snapshot) if model is Review else analyze(obj.snapshot,obj.line,obj.adjusted_at,obj.window_hours,obj.moisture_tolerance)
            obj.status='completed'
            Path('/artifacts').mkdir(exist_ok=True)
            Path(f'/artifacts/{"review" if model is Review else "pairing"}-{obj.id}.json').write_text(json.dumps(obj.result,ensure_ascii=False))
        except Exception as e:obj.status='failed';obj.note=str(e);traceback.print_exc()
        db.commit()
