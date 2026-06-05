import { useEffect, useState } from 'react';
import { tasksApi } from '../services/api';
import type { ScheduledTask } from '../types/index';
import { errorMessage } from '../utils/errors';

export default function TaskScheduler() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningTaskId, setRunningTaskId] = useState<number | null>(null);
  const [runResult, setRunResult] = useState<string | null>(null);

  async function loadTasks() {
    try {
      const response = await tasksApi.getAll();
      setTasks(response.data);
    } catch (error) {
      console.error('Failed to load tasks:', error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTasks();
  }, []);

  const toggleTaskStatus = async (taskId: number, currentStatus: string) => {
    try {
      const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
      await tasksApi.updateStatus(taskId, newStatus);
      void loadTasks();
    } catch (error) {
      console.error('Failed to update task status:', error);
    }
  };

  const runTaskNow = async (taskId: number) => {
    setRunningTaskId(taskId);
    setRunResult(null);
    try {
      const response = await tasksApi.runNow(taskId, { dry_run_submit: true });
      const data = response.data;
      const runId = data.run_id || data.tick?.run_id || 'unknown';
      setRunResult(`${data.ok ? 'Dry-run tick accepted' : 'Tick failed'} · ${runId}`);
      await loadTasks();
    } catch (error: unknown) {
      setRunResult(errorMessage(error, 'Failed to run scheduled task'));
      console.error('Failed to run scheduled task:', error);
    } finally {
      setRunningTaskId(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-tertiary';
      case 'failed':
        return 'text-error';
      default:
        return 'text-outline';
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
    <div className="p-lg technical-grid min-h-full flex flex-col gap-gutter">
      {/* Header Section */}
      <header className="flex justify-between items-end">
        <div>
          <h1 className="font-headline-xl text-headline-xl text-on-surface">Task Scheduler</h1>
          <p className="text-outline font-body-md">
            Manage automated forecast workflows and periodic data aggregation cycles.
          </p>
        </div>
        <button className="bg-primary-container text-on-primary-container px-lg py-sm rounded-lg flex items-center gap-2 font-semibold hover:shadow-[0_0_15px_rgba(0,102,255,0.4)] transition-all">
          <span className="material-symbols-outlined">schedule_send</span>
          <span>Create New Schedule</span>
        </button>
      </header>

      {runResult && (
        <div className="rounded border border-cyan-300/20 bg-cyan-300/10 px-4 py-3 text-sm text-cyan-100">
          {runResult}
        </div>
      )}

      {/* Stats Bento Grid */}
      <div className="grid grid-cols-4 gap-gutter">
        <div className="bg-surface-container border border-white/10 p-md rounded flex flex-col gap-xs">
          <span className="font-label-caps text-label-caps text-outline uppercase">Active Tasks</span>
          <span className="font-data-mono text-3xl font-bold text-tertiary">
            {tasks.filter((t) => t.status === 'active').length}{' '}
            <span className="text-xs font-normal text-slate-500">/ {tasks.length}</span>
          </span>
        </div>
        <div className="bg-surface-container border border-white/10 p-md rounded flex flex-col gap-xs">
          <span className="font-label-caps text-label-caps text-outline uppercase">Next Run</span>
          <span className="font-data-mono text-xl font-bold text-secondary-fixed-dim">
            04:00:00 <span className="text-[10px] text-slate-500 ml-1">UTC</span>
          </span>
        </div>
        <div className="bg-surface-container border border-white/10 p-md rounded flex flex-col gap-xs">
          <span className="font-label-caps text-label-caps text-outline uppercase">Success Rate (24h)</span>
          <span className="font-data-mono text-3xl font-bold text-on-tertiary-container">99.2%</span>
        </div>
        <div className="bg-surface-container border border-white/10 p-md rounded flex flex-col gap-xs">
          <span className="font-label-caps text-label-caps text-outline uppercase">Avg Processing</span>
          <span className="font-data-mono text-3xl font-bold text-primary">14.2s</span>
        </div>
      </div>

      {/* Task Table */}
      <section className="bg-surface-container border border-white/10 rounded flex-1 overflow-hidden flex flex-col">
        <div className="px-md py-sm bg-surface-container-high border-b border-white/10 flex items-center justify-between">
          <span className="font-label-caps text-label-caps text-on-surface-variant">SCHEDULED PIPELINES</span>
          <div className="flex gap-4">
            <button className="text-[10px] text-outline hover:text-white uppercase flex items-center gap-1">
              <span className="material-symbols-outlined text-sm">filter_list</span> Filter
            </button>
            <button className="text-[10px] text-outline hover:text-white uppercase flex items-center gap-1">
              <span className="material-symbols-outlined text-sm">download</span> Export
            </button>
          </div>
        </div>
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left border-collapse">
            <thead className="bg-surface-container-low/50 sticky top-0">
              <tr className="text-outline border-b border-white/5">
                <th className="px-md py-sm font-label-caps text-[10px]">TASK NAME</th>
                <th className="px-md py-sm font-label-caps text-[10px]">STATUS</th>
                <th className="px-md py-sm font-label-caps text-[10px]">EXECUTION TIME</th>
                <th className="px-md py-sm font-label-caps text-[10px]">REGION</th>
                <th className="px-md py-sm font-label-caps text-[10px]">TEMPLATE</th>
                <th className="px-md py-sm font-label-caps text-[10px]">LAST RESULT</th>
                <th className="px-md py-sm font-label-caps text-[10px] text-right">ACTIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {tasks.map((task) => (
                <tr key={task.id} className="hover:bg-white/[0.02] transition-colors group">
                  <td className="px-md py-md">
                    <div className="flex flex-col">
                      <span className="font-bold text-white text-sm">{task.name}</span>
                      <span className="text-[10px] text-slate-500 font-data-mono">{task.task_id}</span>
                    </div>
                  </td>
                  <td className="px-md py-md">
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          task.status === 'active'
                            ? 'bg-tertiary shadow-[0_0_8px_#50e167]'
                            : task.status === 'failed'
                            ? 'bg-error shadow-[0_0_8px_#ffb4ab]'
                            : 'bg-outline'
                        }`}
                      ></div>
                      <span className={`text-xs font-semibold uppercase ${getStatusColor(task.status)}`}>
                        {task.status}
                      </span>
                    </div>
                  </td>
                  <td className="px-md py-md text-xs font-data-mono text-cyan-400">{task.cron_expression}</td>
                  <td className="px-md py-md text-xs text-on-surface">{task.region}</td>
                  <td className="px-md py-md">
                    <span className="bg-surface-container-highest px-2 py-0.5 rounded text-[10px] border border-white/10 uppercase">
                      {templateLabel(task.template)}
                    </span>
                  </td>
                  <td className="px-md py-md">
                    <div
                      className={`flex items-center gap-1.5 text-xs ${
                        task.last_result?.includes('Success') ? 'text-tertiary' : 'text-error'
                      }`}
                    >
                      <span className="material-symbols-outlined text-sm">
                        {task.last_result?.includes('Success') ? 'check_circle' : 'error'}
                      </span>
                      <span>
                        {task.last_result} {task.last_duration && `(${task.last_duration}s)`}
                      </span>
                    </div>
                  </td>
                  <td className="px-md py-md text-right">
                    <div className="flex justify-end gap-2 opacity-40 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => runTaskNow(task.id)}
                        disabled={runningTaskId === task.id || task.status !== 'active'}
                        className="material-symbols-outlined text-slate-400 hover:text-tertiary disabled:opacity-30 disabled:hover:text-slate-400 p-1"
                        title="Run once with dry-run submit"
                      >
                        {runningTaskId === task.id ? 'hourglass_empty' : 'play_circle'}
                      </button>
                      <button className="material-symbols-outlined text-slate-400 hover:text-white p-1">
                        edit
                      </button>
                      <button
                        onClick={() => toggleTaskStatus(task.id, task.status)}
                        className="material-symbols-outlined text-slate-400 hover:text-cyan-400 p-1"
                      >
                        {task.status === 'active' ? 'stop' : 'play_arrow'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function templateLabel(template: string) {
  try {
    const parsed = JSON.parse(template);
    if (parsed && typeof parsed === 'object') {
      const period = parsed.period ?? 'auto';
      const domain = parsed.domain ?? 'domain';
      const days = parsed.forecast_days ?? 7;
      return `${period}/${domain}/${days}d`;
    }
  } catch {
    return template;
  }
  return template;
}
