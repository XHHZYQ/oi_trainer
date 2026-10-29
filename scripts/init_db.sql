-- =====================================================================
-- 数据库初始化脚本（生产 / 开发通用）
-- 使用方式：用 postgres 超级用户执行一次即可
--   psql -U postgres -d io_trainer -f scripts/init_db.sql
-- =====================================================================

-- ① 安装必需的数据库扩展（需要超级用户权限，一次性操作）
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ② 授权应用用户在 public schema 下建表（迁移需要）
GRANT ALL ON SCHEMA public TO CURRENT_USER;

-- ③ 给未来的所有表/序列默认权限（PostgreSQL 10+）
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO CURRENT_USER;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO CURRENT_USER;
