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
