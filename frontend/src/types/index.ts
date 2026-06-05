export interface Workflow {
  id: number;
  name: string;
  description: string;
  template_type: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'paused';
  region: string;
  created_at: string;
  updated_at?: string;
}

export interface WorkflowNode {
  id: number;
  workflow_id: number;
  node_name: string;
  node_type: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'paused';
  progress: number;
  cpu_cores: number;
  memory_gb: number;
  slurm_queue: string;
  walltime: string;
  slurm_job_id?: string;
  error_message?: string;
  created_at: string;
  updated_at?: string;
}

export interface ScheduledTask {
  id: number;
  task_id: string;
  name: string;
  status: 'active' | 'inactive' | 'failed';
  cron_expression: string;
  region: string;
  template: string;
  workflow_id?: number;
  last_run?: string;
  last_result?: string;
  last_duration?: number;
  success_rate: number;
  created_at: string;
  updated_at?: string;
}

export interface ForecastProduct {
  id: number;
  product_name: string;
  product_type: string;
  status: 'ready' | 'archived' | 'error';
  region: string;
  pollen_type: string;
  resolution: string;
  workflow_node: string;
  workflow_version: string;
  file_path: string;
  thumbnail_path?: string;
  is_published: boolean;
  release_time: string;
  created_at: string;
}

export interface SystemLog {
  id: number;
  level: string;
  message: string;
  source: string;
  timestamp: string;
}

export interface DashboardStats {
  active_schedulers: number;
  slurm_jobs_queued: number;
  system_health: number;
  total_workflows: number;
  running_workflows: number;
  failed_workflows: number;
}

export interface DashboardRunSummary {
  run_id: string;
  status: ForecastRunStatus;
  progress: number;
  start_time?: string | null;
  end_time?: string | null;
  period?: string | null;
  domain?: string | null;
  variant?: string | null;
  server_run_dir?: string | null;
  last_error?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface DashboardProductSummary {
  id: number;
  product_name: string;
  product_type: string;
  status: string;
  region?: string | null;
  pollen_type?: string | null;
  resolution?: string | null;
  release_time?: string | null;
}

export interface DashboardFnlSummary {
  total: number;
  server_ok: number;
  uploaded: number;
  needs_repair: number;
}

export interface DashboardOverview {
  stats: DashboardStats;
  runs: DashboardRunSummary[];
  products: {
    total: number;
    ready: number;
    error: number;
    latest: DashboardProductSummary[];
  };
  fnl: DashboardFnlSummary;
  actions: AgentAction[];
  logs: SystemLog[];
}

export type ForecastRunStatus =
  | 'pending'
  | 'ready'
  | 'running'
  | 'success'
  | 'error'
  | 'retrying'
  | 'cancelled';

export interface WrfoutProgress {
  available: boolean;
  reason?: string;
  output_dirs?: string[];
  wrfout_count?: number;
  first_output_path?: string;
  first_forecast_time?: string;
  first_output_mtime?: string;
  latest_output_path?: string;
  latest_forecast_time?: string;
  latest_output_mtime?: string;
  completed_forecast_seconds?: number;
  total_forecast_seconds?: number;
  remaining_forecast_seconds?: number;
  progress?: number;
  eta_seconds?: number | null;
  eta_human?: string | null;
  method?: string;
}

export interface ForecastRunNodeStatus {
  run_id: string;
  node: string;
  status: ForecastRunStatus | 'skipped';
  progress: number;
  attempt: number;
  slurm_job_id?: string | null;
  started_at?: string | null;
  updated_at: string;
  finished_at?: string | null;
  error_code?: string | null;
  message: string;
  log_files: string[];
  wrfout_progress?: WrfoutProgress;
}

export interface ForecastRunWorkflowStatus {
  run_id: string;
  status: ForecastRunStatus;
  progress: number;
  updated_at: string;
  nodes: ForecastRunNodeStatus[];
  run_spec_path?: string;
}

export interface FnlFileStatus {
  valid_time: string;
  file_name: string;
  status: string;
  needs_repair?: boolean;
  source?: string | null;
  server_path?: string | null;
  local_path?: string | null;
  size_bytes?: number | null;
  valid_grib: boolean;
  uploaded?: boolean;
  repair_attempt?: number;
  error_message?: string | null;
  checked_at?: string | null;
}

export interface AgentAction {
  id: number;
  run_id?: string | null;
  action_type: string;
  reason?: string | null;
  status: string;
  input_json?: string | null;
  output_json?: string | null;
  created_at?: string | null;
  finished_at?: string | null;
}

export interface FlowResponse<T = unknown> {
  ok: boolean;
  data: T;
}
