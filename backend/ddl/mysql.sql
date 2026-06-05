-- SManager MySQL schema baseline.
-- Keep this file in sync with backend/app/models/models.py and backend/app/core/migrations.py.
-- Target: MySQL 8.0, utf8mb4.

CREATE DATABASE IF NOT EXISTS smanager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smanager;

CREATE TABLE IF NOT EXISTS workflows (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(255),
  description TEXT,
  template_type VARCHAR(255),
  status ENUM('PENDING','RUNNING','SUCCESS','FAILED','PAUSED'),
  region VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_workflows_name (name),
  KEY ix_workflows_id (id),
  KEY ix_workflows_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS workflow_nodes (
  id INT NOT NULL AUTO_INCREMENT,
  workflow_id INT,
  node_name VARCHAR(255),
  node_type VARCHAR(255),
  status ENUM('PENDING','RUNNING','SUCCESS','FAILED','PAUSED'),
  progress FLOAT,
  cpu_cores INT,
  memory_gb INT,
  slurm_queue VARCHAR(255),
  walltime VARCHAR(255),
  slurm_job_id VARCHAR(255) NULL,
  error_message TEXT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  PRIMARY KEY (id),
  KEY ix_workflow_nodes_id (id),
  KEY ix_workflow_nodes_workflow_id (workflow_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS scheduled_tasks (
  id INT NOT NULL AUTO_INCREMENT,
  task_id VARCHAR(255),
  name VARCHAR(255),
  status ENUM('ACTIVE','INACTIVE','FAILED'),
  cron_expression VARCHAR(255),
  region VARCHAR(255),
  template TEXT,
  workflow_id INT NULL,
  last_run DATETIME NULL,
  last_result VARCHAR(255) NULL,
  last_duration FLOAT NULL,
  success_rate FLOAT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_scheduled_tasks_task_id (task_id),
  KEY ix_scheduled_tasks_id (id),
  KEY ix_scheduled_tasks_task_id (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS forecast_products (
  id INT NOT NULL AUTO_INCREMENT,
  product_name VARCHAR(255),
  product_type VARCHAR(255),
  status ENUM('READY','ARCHIVED','ERROR'),
  region VARCHAR(255),
  pollen_type VARCHAR(255),
  resolution VARCHAR(255),
  workflow_node VARCHAR(255),
  workflow_version VARCHAR(255),
  file_path VARCHAR(255),
  subtype VARCHAR(255) NULL,
  variable VARCHAR(255) NULL,
  unit VARCHAR(255) NULL,
  bounds_json TEXT NULL,
  lead_time VARCHAR(255) NULL,
  source_run_id VARCHAR(255) NULL,
  capability_status VARCHAR(255) NULL,
  thumbnail_path VARCHAR(255) NULL,
  is_published BOOL,
  release_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_forecast_products_product_name (product_name),
  KEY ix_forecast_products_id (id),
  KEY ix_forecast_products_product_name (product_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS system_logs (
  id INT NOT NULL AUTO_INCREMENT,
  level VARCHAR(255),
  message TEXT,
  source VARCHAR(255),
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_system_logs_id (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS forecast_runs (
  id INT NOT NULL AUTO_INCREMENT,
  run_id VARCHAR(255),
  start_time VARCHAR(255),
  end_time VARCHAR(255),
  period VARCHAR(255),
  domain VARCHAR(255),
  variant VARCHAR(255),
  met_provider VARCHAR(255),
  status ENUM('PENDING','READY','RUNNING','SUCCESS','ERROR','RETRYING','CANCELLED'),
  progress FLOAT,
  server_run_dir VARCHAR(255) NULL,
  last_error TEXT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_forecast_runs_run_id (run_id),
  KEY ix_forecast_runs_id (id),
  KEY ix_forecast_runs_run_id (run_id),
  KEY ix_forecast_runs_start_time (start_time),
  KEY ix_forecast_runs_end_time (end_time),
  KEY ix_forecast_runs_period (period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS forecast_run_nodes (
  id INT NOT NULL AUTO_INCREMENT,
  run_id VARCHAR(255),
  node_name VARCHAR(255),
  status VARCHAR(255),
  progress FLOAT,
  attempt INT,
  slurm_job_id VARCHAR(255) NULL,
  error_code VARCHAR(255) NULL,
  message TEXT NULL,
  updated_at DATETIME NULL,
  PRIMARY KEY (id),
  KEY ix_forecast_run_nodes_id (id),
  KEY ix_forecast_run_nodes_run_id (run_id),
  KEY ix_forecast_run_nodes_node_name (node_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS forecast_run_events (
  id INT NOT NULL AUTO_INCREMENT,
  event_key VARCHAR(255),
  run_id VARCHAR(255),
  node_name VARCHAR(255) NULL,
  event_type VARCHAR(255),
  level VARCHAR(255),
  message TEXT,
  payload_json TEXT NULL,
  created_at VARCHAR(255),
  synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_forecast_run_events_event_key (event_key),
  KEY ix_forecast_run_events_id (id),
  KEY ix_forecast_run_events_event_key (event_key),
  KEY ix_forecast_run_events_run_id (run_id),
  KEY ix_forecast_run_events_node_name (node_name),
  KEY ix_forecast_run_events_event_type (event_type),
  KEY ix_forecast_run_events_level (level),
  KEY ix_forecast_run_events_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS fnl_file_records (
  id INT NOT NULL AUTO_INCREMENT,
  valid_time VARCHAR(255),
  file_name VARCHAR(255),
  status VARCHAR(255),
  source VARCHAR(255) NULL,
  server_path VARCHAR(255) NULL,
  local_path VARCHAR(255) NULL,
  size_bytes INT NULL,
  valid_grib BOOL,
  uploaded BOOL,
  repair_attempt INT,
  error_message TEXT NULL,
  checked_at VARCHAR(255) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_fnl_file_records_id (id),
  KEY ix_fnl_file_records_valid_time (valid_time),
  KEY ix_fnl_file_records_file_name (file_name),
  KEY ix_fnl_file_records_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS agent_actions (
  id INT NOT NULL AUTO_INCREMENT,
  run_id VARCHAR(255) NULL,
  action_type VARCHAR(255),
  reason TEXT NULL,
  status VARCHAR(255),
  input_json TEXT NULL,
  output_json TEXT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  finished_at DATETIME NULL,
  PRIMARY KEY (id),
  KEY ix_agent_actions_id (id),
  KEY ix_agent_actions_run_id (run_id),
  KEY ix_agent_actions_action_type (action_type),
  KEY ix_agent_actions_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS schema_migrations (
  id INT NOT NULL AUTO_INCREMENT,
  version VARCHAR(255),
  description TEXT,
  applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_schema_migrations_version (version),
  KEY ix_schema_migrations_id (id),
  KEY ix_schema_migrations_version (version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
