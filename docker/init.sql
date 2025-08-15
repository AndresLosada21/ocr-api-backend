-- Script de inicialização do banco PostgreSQL
-- Executado automaticamente na criação do container

-- Definir timezone como UTC
SET timezone = 'UTC';

-- Criar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Criar tipos ENUM customizados
CREATE TYPE job_type AS ENUM ('ocr', 'barcode', 'qrcode', 'all');
CREATE TYPE job_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled');

-- Função para atualizar timestamp automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Função para estatísticas de sessão de usuário
CREATE OR REPLACE FUNCTION update_session_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Atualizar estatísticas de sessão do usuário
    INSERT INTO user_sessions (
        session_id, 
        client_ip, 
        user_agent, 
        total_jobs, 
        jobs_today, 
        last_seen,
        last_job_date
    )
    VALUES (
        NEW.session_id, 
        NEW.client_ip, 
        NEW.user_agent, 
        1, 
        1, 
        NOW(),
        CURRENT_DATE
    )
    ON CONFLICT (session_id) 
    DO UPDATE SET
        total_jobs = user_sessions.total_jobs + 1,
        jobs_today = CASE 
            WHEN user_sessions.last_job_date = CURRENT_DATE 
            THEN user_sessions.jobs_today + 1 
            ELSE 1 
        END,
        last_job_date = CURRENT_DATE,
        last_seen = NOW(),
        user_agent = COALESCE(NEW.user_agent, user_sessions.user_agent);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Função para limpeza automática de dados antigos
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Remover jobs muito antigos (configurável via settings)
    DELETE FROM processing_jobs 
    WHERE created_at < NOW() - INTERVAL '90 days';
    
    -- Remover sessões inativas antigas
    DELETE FROM user_sessions 
    WHERE last_seen < NOW() - INTERVAL '30 days';
    
    -- Log da limpeza
    RAISE NOTICE 'Limpeza de dados antigos executada em %', NOW();
END;
$$ LANGUAGE plpgsql;

-- Função para obter estatísticas gerais
CREATE OR REPLACE FUNCTION get_api_statistics(
    period_days INTEGER DEFAULT 7
)
RETURNS TABLE (
    total_jobs BIGINT,
    successful_jobs BIGINT,
    failed_jobs BIGINT,
    success_rate NUMERIC,
    avg_processing_time_ms NUMERIC,
    ocr_jobs BIGINT,
    barcode_jobs BIGINT,
    qrcode_jobs BIGINT,
    unique_sessions BIGINT,
    top_language TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH job_stats AS (
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'completed') as successful,
            COUNT(*) FILTER (WHERE status = 'failed') as failed,
            AVG(processing_time_ms) FILTER (WHERE processing_time_ms IS NOT NULL) as avg_time,
            COUNT(*) FILTER (WHERE job_type = 'ocr') as ocr_count,
            COUNT(*) FILTER (WHERE job_type = 'barcode') as barcode_count,
            COUNT(*) FILTER (WHERE job_type = 'qrcode') as qrcode_count,
            COUNT(DISTINCT session_id) as sessions
        FROM processing_jobs 
        WHERE created_at >= NOW() - INTERVAL '%s days' % period_days
    ),
    language_stats AS (
        SELECT processing_params->>'language' as lang
        FROM processing_jobs 
        WHERE job_type = 'ocr' 
          AND created_at >= NOW() - INTERVAL '%s days' % period_days
          AND processing_params->>'language' IS NOT NULL
        GROUP BY processing_params->>'language'
        ORDER BY COUNT(*) DESC
        LIMIT 1
    )
    SELECT 
        js.total,
        js.successful,
        js.failed,
        CASE 
            WHEN js.total > 0 THEN ROUND((js.successful::NUMERIC / js.total) * 100, 2)
            ELSE 0
        END,
        ROUND(js.avg_time, 2),
        js.ocr_count,
        js.barcode_count,
        js.qrcode_count,
        js.sessions,
        COALESCE(ls.lang, 'unknown')
    FROM job_stats js
    LEFT JOIN language_stats ls ON true;
END;
$$ LANGUAGE plpgsql;

-- Usuário somente leitura para analytics
CREATE USER ocr_readonly WITH PASSWORD 'readonly123';
GRANT CONNECT ON DATABASE ocr_api TO ocr_readonly;

-- Configurações de performance
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Configurações específicas para aplicação
ALTER SYSTEM SET log_statement = 'none';
ALTER SYSTEM SET log_min_duration_statement = 1000;
ALTER SYSTEM SET track_activity_query_size = 2048;

-- Comentários informativos
COMMENT ON DATABASE ocr_api IS 'Banco de dados para OCR API Backend - Processamento de OCR, Barcode e QRCode';

-- Log de inicialização
DO $$
BEGIN
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'OCR API Database initialized successfully!';
    RAISE NOTICE 'Database: ocr_api';
    RAISE NOTICE 'Extensions: uuid-ossp, pg_stat_statements';
    RAISE NOTICE 'Custom types: job_type, job_status';
    RAISE NOTICE 'Timezone: UTC';
    RAISE NOTICE '===========================================';
END $$;