-- docker/indexes.sql
-- Índices otimizados para performance

-- Índices em processing_jobs
CREATE INDEX idx_processing_jobs_status ON processing_jobs (status);
CREATE INDEX idx_processing_jobs_type ON processing_jobs (job_type);
CREATE INDEX idx_processing_jobs_created_at ON processing_jobs (created_at DESC);
CREATE INDEX idx_processing_jobs_client_ip ON processing_jobs (client_ip);
CREATE INDEX idx_processing_jobs_session_id ON processing_jobs (session_id);

-- Índices compostos
CREATE INDEX idx_jobs_type_status ON processing_jobs (job_type, status);
CREATE INDEX idx_jobs_created_status ON processing_jobs (created_at, status);

-- Para resultados (assumindo tabelas)
-- Para barcode_results (se existir)
CREATE INDEX idx_barcode_results_job_id ON barcode_results (job_id);
CREATE INDEX idx_barcode_results_type ON barcode_results (barcode_type);

-- Para ocr_results (se existir)
CREATE INDEX idx_ocr_results_job_id ON ocr_results (job_id);
CREATE INDEX idx_ocr_results_language ON ocr_results (language);

-- Para qrcode_results (se existir)
CREATE INDEX idx_qrcode_results_job_id ON qrcode_results (job_id);

-- Otimização de queries de analytics
ANALYZE processing_jobs;