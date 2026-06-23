import { useEffect, useState, type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { SlurmSummary, StatusPill } from '../components/RunDisplay';
import { useI18n } from '../i18n';
import { runNavState } from '../hooks/useRunNavigation';
import { dashboardApi, productsApi, runDetailPath } from '../services/api';
import type { AgentAction, DashboardOverview, SystemLog } from '../types/index';
import { errorMessage } from '../utils/errors';

export default function Dashboard() {
  const { t } = useI18n();
  const location = useLocation();
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadOverview() {
    setLoading(true);
    setError('');
    try {
      const response = await dashboardApi.getOverview({ recent_limit: 10 });
      setOverview(response.data);
    } catch (err: unknown) {
      setError(errorMessage(err, 'Failed to load dashboard overview'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadOverview();
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="font-data-mono text-cyan-400">{t('loadingDashboard')}</div>
      </div>
    );
  }

  const stats = overview?.stats;
  const fnl = overview?.fnl;
  const server = overview?.server;
  const detailNav = runNavState(location.pathname, t('dashboardTitle'));

  return (
    <div className="min-h-full p-6 technical-grid">
      <header className="mb-8 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <h1 className="mb-1 font-headline-xl text-headline-xl text-on-background">{t('dashboardTitle')}</h1>
          <p className="font-body-md text-on-surface-variant">{t('dashboardSubtitle')}</p>
          {overview?.stale && (
            <p className="mt-2 text-xs text-amber-300">服务器暂不可达，部分数据来自本地缓存。</p>
          )}
        </div>
        <button
          onClick={loadOverview}
          className="w-fit rounded-lg border border-white/10 bg-surface-container-high px-md py-sm text-sm text-on-surface hover:bg-white/10"
        >
          <span className="material-symbols-outlined mr-2 align-middle text-sm">refresh</span>
          {t('refresh')}
        </button>
      </header>

      {error && <div className="mb-6 rounded-lg border border-error/30 bg-error-container/20 p-md text-sm text-error">{error}</div>}

      {server?.daemon && (
        <section className="mb-8 grid grid-cols-1 gap-gutter md:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="服务器时间" value={formatShort(server.server_time_local)} icon="schedule" tone="info" />
          <MetricCard
            label="定时调度"
            value={server.config?.schedule_enabled ?? server.daemon.schedule_enabled ? '运行中' : '已停止'}
            icon="timer"
            tone={server.config?.schedule_enabled ?? server.daemon.schedule_enabled ? 'ok' : 'info'}
          />
          <MetricCard label="下次 Tick" value={formatShort(server.daemon.next_tick_at)} icon="event" tone="info" />
          <MetricCard label="活跃 Run" value={`${server.daemon.active_runs ?? 0}`} icon="rocket_launch" tone="info" />
        </section>
      )}

      {server?.config?.regions && server.config.regions.length > 0 && (
        <section className="mb-8 rounded-lg border border-white/10 bg-surface-container p-md">
          <p className="mb-2 font-label-caps text-label-caps uppercase text-outline">当前预报区域</p>
          <p className="text-xs text-on-surface-variant">
            {server.config.regions.length} 个区域：{server.config.regions.join(', ')}
          </p>
        </section>
      )}

      {server?.daemon && (
        <section className="mb-8 grid grid-cols-1 gap-gutter md:grid-cols-2 xl:grid-cols-2">
          <MetricCard label="上次 Tick" value={server.daemon.last_tick_result || '-'} icon="play_circle" tone="ok" />
          <MetricCard label="待补 FNL" value={`${server.daemon.pending_repairs ?? 0}`} icon="cloud_sync" tone={(server.daemon.pending_repairs ?? 0) > 0 ? 'danger' : 'ok'} />
        </section>
      )}

      <section className="mb-8 grid grid-cols-1 gap-gutter md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label={t('systemHealth')} value={`${stats?.system_health ?? 100}%`} icon="health_and_safety" tone="ok" />
        <MetricCard label={t('runningRuns')} value={`${stats?.running_workflows ?? 0}/${stats?.total_workflows ?? 0}`} icon="play_circle" tone="info" />
        <MetricCard label={t('fnlNeedsRepair')} value={`${fnl?.needs_repair ?? 0}`} icon="cloud_sync" tone={(fnl?.needs_repair ?? 0) > 0 ? 'danger' : 'ok'} />
        <MetricCard label={t('readyProducts')} value={`${overview?.products.ready ?? 0}/${overview?.products.total ?? 0}`} icon="analytics" tone="info" />
      </section>

      <section className="mb-8 grid grid-cols-1 gap-gutter xl:grid-cols-[1.4fr_0.6fr]">
        <Panel
          title={t('recentRuns')}
          action={
            <Link
              to="/admin/runs/list"
              className="inline-flex items-center gap-1 text-[10px] text-cyan-300 hover:text-cyan-200"
            >
              {t('viewAllRuns')}
              <span className="material-symbols-outlined text-sm">arrow_forward</span>
            </Link>
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="border-b border-white/10 text-outline">
                <tr>
                  <th className="px-sm py-sm text-[10px]">{t('run')}</th>
                  <th className="px-sm py-sm text-[10px]">{t('status')}</th>
                  <th className="px-sm py-sm text-[10px]">{t('progress')}</th>
                  <th className="px-sm py-sm text-[10px]">Slurm</th>
                  <th className="px-sm py-sm text-[10px]">{t('window')}</th>
                  <th className="px-sm py-sm text-[10px]">{t('domain')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {(overview?.runs ?? []).map((run) => (
                  <tr key={run.run_key || run.run_id} className="hover:bg-white/[0.03]">
                    <td className="max-w-[260px] px-sm py-sm">
                      <Link
                        to={runDetailPath(run)}
                        state={detailNav}
                        className="font-data-mono text-xs text-cyan-300 hover:text-cyan-200"
                      >
                        {run.run_key || run.run_id}
                      </Link>
                      {run.last_error && (
                        <p className="mt-0.5 truncate text-[10px] text-error">{String(run.last_error)}</p>
                      )}
                    </td>
                    <td className="px-sm py-sm"><StatusPill status={run.status} /></td>
                    <td className="px-sm py-sm text-xs text-on-surface">{run.progress}%</td>
                    <td className="px-sm py-sm text-xs text-outline">
                      <SlurmSummary run={run} />
                    </td>
                    <td className="px-sm py-sm text-xs text-outline">{run.period || '-'} / {run.start_time || '-'}</td>
                    <td className="px-sm py-sm text-xs text-outline">{run.domain || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(overview?.runs.length ?? 0) === 0 && <EmptyState text={t('noRuns')} />}
          </div>
        </Panel>

        <Panel title={t('fnlCoverage')}>
          <div className="space-y-sm">
            <SummaryRow label={t('serverOk')} value={fnl?.server_ok ?? 0} />
            <SummaryRow label={t('uploaded')} value={fnl?.uploaded ?? 0} />
            <SummaryRow label={t('needsRepair')} value={fnl?.needs_repair ?? 0} danger={(fnl?.needs_repair ?? 0) > 0} />
            <SummaryRow label={t('totalRecords')} value={fnl?.total ?? 0} />
          </div>
          <Link to="/admin/fnl" className="mt-md inline-flex items-center gap-1 text-xs text-cyan-300 hover:text-cyan-200">
            {t('openFnlManager')}
            <span className="material-symbols-outlined text-sm">arrow_forward</span>
          </Link>
        </Panel>
      </section>

      <section className="mb-8 grid grid-cols-1 gap-gutter xl:grid-cols-2">
        <Panel title={t('latestProducts')}>
          <div className="max-h-80 space-y-sm overflow-auto">
            {(overview?.products.latest ?? []).map((product) => (
              <div key={product.id} className="flex items-center justify-between gap-sm rounded border border-white/10 bg-surface-container-low p-sm">
                <div className="min-w-0">
                  <p className="truncate font-data-mono text-xs text-cyan-300">{product.product_name}</p>
                  <p className="text-[10px] text-outline">{product.product_type} / {product.pollen_type || 'unknown'} / {product.resolution || 'unknown'}</p>
                </div>
                <a
                  href={productsApi.downloadUrl(product.id)}
                  className="rounded bg-primary-container px-2 py-1 text-[10px] font-semibold text-on-primary-container"
                >
                  {t('download')}
                </a>
              </div>
            ))}
            {(overview?.products.latest.length ?? 0) === 0 && <EmptyState text={t('noProducts')} />}
          </div>
        </Panel>

        <Panel title={t('hermesActions')}>
          <div className="max-h-80 space-y-sm overflow-auto">
            {(overview?.actions ?? []).map((action) => (
              <ActionItem key={action.id} action={action} />
            ))}
            {(overview?.actions.length ?? 0) === 0 && <EmptyState text={t('noActions')} />}
          </div>
        </Panel>
      </section>

      <Panel title={t('systemLogs')}>
        <div className="max-h-80 space-y-2 overflow-y-auto font-data-mono text-xs">
          {(overview?.logs ?? []).map((log) => (
            <LogRow key={log.id} log={log} />
          ))}
          {(overview?.logs.length ?? 0) === 0 && <EmptyState text={t('noLogs')} />}
        </div>
      </Panel>
    </div>
  );
}

function MetricCard({
  label,
  value,
  icon,
  tone,
}: {
  label: string;
  value: string;
  icon: string;
  tone: 'ok' | 'info' | 'danger';
}) {
  const color = tone === 'danger' ? 'text-error' : tone === 'ok' ? 'text-tertiary' : 'text-cyan-400';
  return (
    <div className="rounded-lg border border-white/10 bg-surface-container p-md">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-label-caps text-label-caps uppercase text-outline">{label}</span>
        <span className={`material-symbols-outlined ${color}`}>{icon}</span>
      </div>
      <p className={`font-data-mono text-3xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function Panel({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-white/10 bg-surface-container">
      <div className="flex items-center justify-between border-b border-white/10 bg-surface-container-high px-md py-sm">
        <span className="font-label-caps text-label-caps uppercase text-on-surface-variant">{title}</span>
        {action}
      </div>
      <div className="p-md">{children}</div>
    </div>
  );
}

function SummaryRow({ label, value, danger = false }: { label: string; value: number; danger?: boolean }) {
  return (
    <div className="flex items-center justify-between rounded border border-white/10 bg-surface-container-low px-sm py-xs">
      <span className="text-xs text-outline">{label}</span>
      <span className={`font-data-mono text-sm ${danger ? 'text-error' : 'text-on-surface'}`}>{value}</span>
    </div>
  );
}

function ActionItem({ action }: { action: AgentAction }) {
  return (
    <div className="rounded border border-white/10 bg-surface-container-low p-sm">
      <div className="flex items-center justify-between gap-sm">
        <span className="font-data-mono text-xs text-cyan-300">{action.action_type}</span>
        <StatusPill status={action.status} />
      </div>
      <p className="mt-xs text-xs text-on-surface-variant">{action.reason || '-'}</p>
      <p className="mt-xs text-[10px] text-outline">{action.run_id || 'global'} / {formatDate(action.created_at)}</p>
    </div>
  );
}

function LogRow({ log }: { log: SystemLog }) {
  const color = log.level === 'ERROR' ? 'text-error' : log.level === 'INFO' ? 'text-tertiary' : 'text-primary';
  return (
    <div className="flex gap-4">
      <span className="shrink-0 text-slate-600">{formatDate(log.timestamp)}</span>
      <span className={`font-bold ${color}`}>[{log.level}]</span>
      <span className="text-on-surface">{log.message}</span>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <p className="text-sm text-outline">{text}</p>;
}

function formatDate(value?: string | null) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

function formatShort(value?: string | null) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}
