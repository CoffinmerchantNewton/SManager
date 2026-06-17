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
  subtype?: string | null;
  variable?: string | null;
  unit?: string | null;
  bounds?: {
    west: number;
    south: number;
    east: number;
    north: number;
  } | null;
  bounds_json?: string | null;
  lead_time?: string | null;
  source_run_id?: string | null;
  capability_status?: string | null;
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

export interface ServerRegionInfo {
  region: string;
  display_name: string;
  seasons: string[];
  slurm_code: string;
}

export interface ServerForecastConfig {
  season: string;
  pre: string;
  regions: string[];
  fnl_gfs_default: number;
  fnl_gfs_fallback: number;
  task_dup_action?: string;
}

export interface ServerScheduleConfig {
  enabled: boolean;
  tick_time: string;
  timezone: string;
  repair_deadline: string;
  poll_interval: number;
}

export interface ServerConfig {
  schedule: ServerScheduleConfig;
  forecast: ServerForecastConfig;
}

export interface ServerDaemonStatus {
  started_at?: string;
  schedule_enabled?: boolean;
  last_tick_at?: string | null;
  last_tick_result?: string | null;
  next_tick_at?: string | null;
  last_reconcile_at?: string | null;
  active_runs?: number;
  pending_repairs?: number;
  server_time_utc?: string;
  server_time_local?: string;
}

export interface RunStateStep {
  status?: string;
  started_at?: string;
  finished_at?: string;
}

export interface RunStateJson {
  version?: number;
  tag?: string;
  updated_at?: string;
  steps?: Record<string, RunStateStep | string>;
  failure?: string | { step?: string; stage?: string; message?: string; error?: string } | null;
  geogrid?: string;
  linkgrib?: string;
  ungrib?: string;
  metgrid?: string;
  real?: string;
  wrfchemi?: string;
  wrf?: string;
  postprocess?: string;
  wps?: string;
}

export interface ServerRunSummary {
  run_key: string;
  run_id: string;
  season: string;
  region: string;
  pre?: string;
  start_date?: string;
  status: ForecastRunStatus;
  progress: number;
  server_run_dir?: string | null;
  state?: RunStateJson;
  effective_state?: Record<string, string>;
  failure?: RunStateJson['failure'];
  slurm_jobs?: Array<{ job_id: string; name: string; state: string; time?: string }>;
  nodes?: ForecastRunNodeStatus[];
}

export interface DashboardRunSummary {
  run_key?: string;
  run_id: string;
  status: ForecastRunStatus | string;
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
  slurm_jobs?: Array<{ job_id: string; name: string; state: string; time?: string; exit_code?: string }>;
  slurm_job_ids?: string[];
  slurm_active_count?: number;
  anomalies?: string[];
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
  pending_requests?: Array<Record<string, unknown>>;
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
  server?: {
    daemon?: ServerDaemonStatus;
    config?: {
      season?: string;
      regions?: string[];
      schedule_enabled?: boolean;
      tick_time?: string;
      timezone?: string;
    };
    source?: string;
    stale?: boolean;
    server_time_local?: string;
    server_time_utc?: string;
  };
  source?: string;
  stale?: boolean;
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
  run_id?: string;
  node: string;
  stage?: string;
  status: ForecastRunStatus | 'skipped';
  progress: number;
  attempt: number;
  slurm_job_id?: string | null;
  slurm_job_name?: string | null;
  slurm_state?: string | null;
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
  valid_grib?: boolean;
  uploaded?: boolean;
  repair_attempt?: number;
  error_message?: string | null;
  checked_at?: string | null;
  region?: string | null;
  date?: string | null;
  hour?: string | null;
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
