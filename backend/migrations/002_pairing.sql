-- Schema is applied by SQLAlchemy metadata.create_all at application start;
-- src.config.database.ensure_schema applies these column additions idempotently
-- for deployments upgrading an existing inspections table.
-- 002: 调参前后配对分析
-- inspections.sampled_at 实际采样时刻，旧样本为 NULL 表示时间未知；
-- inspections.created_at 提交时刻，配对分析以受理时已提交的记录为准。
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS sampled_at timestamptz;
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS created_at timestamptz;
-- pairings 表由 create_all 建立：保存调参时刻 adjusted_at、等长窗口 window_hours、
-- 水分差上限 moisture_tolerance、受理时刻 accepted_at、冻结快照 snapshot 与结果 result。
