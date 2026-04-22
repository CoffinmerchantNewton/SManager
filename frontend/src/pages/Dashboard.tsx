import { useEffect, useState } from 'react';
import { dashboardApi } from '../services/api';
import type { DashboardStats, SystemLog } from '../types/index';

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [logs, setLogs] = useState<SystemLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [statsRes, logsRes] = await Promise.all([
        dashboardApi.getStats(),
        dashboardApi.getLogs({ limit: 10 }),
      ]);
      setStats(statsRes.data);
      setLogs(logsRes.data);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-full">
        <div className="text-cyan-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="p-6 technical-grid min-h-full">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-headline-xl text-headline-xl text-on-background mb-1">预报管理中心</h1>
        <p className="text-on-surface-variant font-body-md">
          Real-time monitoring and control center for pollen forecast operations
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-gutter mb-8">
        <div className="bg-surface-container border border-white/10 p-md rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <span className="font-label-caps text-label-caps text-outline uppercase">Active Schedulers</span>
            <span className="material-symbols-outlined text-tertiary">schedule</span>
          </div>
          <p className="font-data-mono text-3xl font-bold text-tertiary">{stats?.active_schedulers || 0}</p>
        </div>

        <div className="bg-surface-container border border-white/10 p-md rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <span className="font-label-caps text-label-caps text-outline uppercase">Slurm Jobs Queued</span>
            <span className="material-symbols-outlined text-cyan-400">queue</span>
          </div>
          <p className="font-data-mono text-3xl font-bold text-cyan-400">{stats?.slurm_jobs_queued || 0}</p>
        </div>

        <div className="bg-surface-container border border-white/10 p-md rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <span className="font-label-caps text-label-caps text-outline uppercase">System Health</span>
            <span className="material-symbols-outlined text-tertiary">health_and_safety</span>
          </div>
          <p className="font-data-mono text-3xl font-bold text-tertiary">{stats?.system_health || 0}%</p>
        </div>

        <div className="bg-surface-container border border-white/10 p-md rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <span className="font-label-caps text-label-caps text-outline uppercase">Running Workflows</span>
            <span className="material-symbols-outlined text-primary">play_circle</span>
          </div>
          <p className="font-data-mono text-3xl font-bold text-primary">
            {stats?.running_workflows || 0}
            <span className="text-xs text-slate-500 ml-2">/ {stats?.total_workflows || 0}</span>
          </p>
        </div>
      </div>

      {/* System Logs */}
      <div className="bg-surface-container border border-white/10 rounded-xl overflow-hidden">
        <div className="px-md py-sm bg-surface-container-high border-b border-white/10">
          <span className="font-label-caps text-label-caps text-on-surface-variant">SYSTEM LOGS</span>
        </div>
        <div className="p-md space-y-2 font-data-mono text-xs max-h-96 overflow-y-auto">
          {logs.map((log) => (
            <div key={log.id} className="flex gap-4">
              <span className="text-slate-600 shrink-0">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span
                className={`font-bold ${
                  log.level === 'ERROR'
                    ? 'text-error'
                    : log.level === 'INFO'
                    ? 'text-tertiary'
                    : 'text-primary'
                }`}
              >
                [{log.level}]
              </span>
              <span className="text-on-surface">{log.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
