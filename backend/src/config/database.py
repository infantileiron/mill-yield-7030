from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from src.config.settings import DATABASE_URL
engine=create_engine(DATABASE_URL, pool_pre_ping=True)
Session=sessionmaker(engine, expire_on_commit=False)
class Base(DeclarativeBase): pass
def get_db():
    with Session() as s: yield s
def ensure_schema():
    # create_all 不会给既有表补列；为升级部署幂等补齐新增列（旧行 sampled_at/created_at 为 NULL）
    with engine.begin() as c:
        c.execute(text("ALTER TABLE inspections ADD COLUMN IF NOT EXISTS sampled_at timestamptz"))
        c.execute(text("ALTER TABLE inspections ADD COLUMN IF NOT EXISTS created_at timestamptz"))
