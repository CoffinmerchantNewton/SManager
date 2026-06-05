import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { dashboardApi, productsApi } from '../services/api';
import type { AgentAction, DashboardOverview, SystemLog } from '../types/index';
import { errorMessage } from '../utils/errors';

export default function Dashboard() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadOverview() {
    setLoading(true);
    setError('');
    try {
      const response = await dashboardApi.getOverview({ recent_limit: 8 });
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
        <div className="font-data-mono text-cyan-400">Loading dashboard...</div>
      </div>
    );
  }

  const stats = overview?.stats;
  const fnl = overview?.fnl;

  return (
    <div className="min-h-full p-6 technical-grid">
      <header className="mb-8 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <h1 className="font-headline-xl text-headline-xl text-on-background mb-1">预报管理中心</h1>
          <p className="text-on-surface-variant font-body-md">
            Daily operations view for WRF-Pollen runs, FNL coverage, products, and AI actions.
          </p>
        </div>
        <button
          onClick={loadOverview}
          className="w-fit rounded-lg border border-white/10 bg-surface-container-high px-md py-sm text-sm text-on-surface hover:bg-white/10"
        >
          <span className="material-symbols-outlined align-middle mr-2 text-sm">refresh</span>
          Refresh
        </button>
      </header>

      {error && <div className="mb-6 rounded-lg border border-error/30 bg-error-container/20 p-md text-sm text-error">{error}</div>}

      <section className="mb-8 grid grid-cols-1 gap-gutter md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="System Health" value={`${stats?.system_health ?? 100}%`} icon="health_and_safety" tone="ok" />
        <MetricCard label="Running Runs" value={`${stats?.running_workflows ?? 0}/${stats?.total_workflows ?? 0}`} icon="play_circle" tone="info" />
        <MetricCard label="FNL Needs Repair" value={`${fnl?.needs_repair ?? 0}`} icon="cloud_sync" tone={(fnl?.needs_repair ?? 0) > 0 ? 'danger' : 'ok'} />
        <MetricCard label="Ready Products" value={`${overview?.products.ready ?? 0}/${overview?.products.total ?? 0}`} icon="analytics" tone="info" />
      </section>

      <section className="mb-8 grid grid-cols-1 gap-gutter xl:grid-cols-[1.4fr_0.6fr]">
        <Panel title="Recent Runs">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="border-b border-white/10 text-outline">
                <tr>
                  <th className="px-sm py-sm text-[10px]">RUN</th>
                  <th className="px-sm py-sm text-[10px]">STATUS</th>
                  <th className="px-sm py-sm text-[10px]">PROGRESS</th>
                  <th className="px-sm py-sm text-[10px]">WINDOW</th>
                  <th className="px-sm py-sm text-[10px]">DOMAIN</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {(overview?.runs ?? []).map((run) => (
                  <tr key={run.run_id} className="hover:bg-white/[0.03]">
                    <td className="max-w-[260px] px-sm py-sm">
                      <Link to={`/admin/runs/${encodeURIComponent(run.run_id)}`} className="font-data-mono text-xs text-cyan-300 hover:text-cyan-200">
                        {run.run_id}
                      </Link>
                    </td>
                    <td className="px-sm py-sm"><StatusPill status={run.status} /></td>
                    <td className="px-sm py-sm text-xs text-on-surface">{run.progress}%</td>
                    <td className="px-sm py-sm text-xs text-outline">{run.start_time || '-'} {'->'} {run.end_time || '-'}</td>
                    <td className="px-sm py-sm text-xs text-outline">{run.domain || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(overview?.runs.length ?? 0) === 0 && <EmptyState text="No forecast runs synced yet." />}
          </div>
        </Panel>

        <Panel title="FNL Coverage">
          <div className="space-y-sm">
            <SummaryRow label="Server OK" value={fnl?.server_ok ?? 0} />
            <SummaryRow label="Uploaded" value={fnl?.uploaded ?? 0} />
            <SummaryRow label="Needs Repair" value={fnl?.needs_repair ?? 0} danger={(fnl?.needs_repair ?? 0) > 0} />
            <SummaryRow label="Total Records" value={fnl?.total ?? 0} />
          </div>
          <Link to="/admin/fnl" className="mt-md inline-flex items-center gap-1 text-xs text-cyan-300 hover:text-cyan-200">
            Open FNL Manager
            <span className="material-symbols-outlined text-sm">arrow_forward</span>
          </Link>
        </Panel>
      </section>

      <section className="mb-8 grid grid-cols-1 gap-gutter xl:grid-cols-2">
        <Panel title="Latest Products">
          <div className="space-y-sm max-h-80 overflow-auto">
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
                  Download
                </a>
              </div>
            ))}
            {(overview?.products.latest.length ?? 0) === 0 && <EmptyState text="No synced products yet." />}
          </div>
        </Panel>

        <Panel title="Hermes / AI Actions">
          <div className="space-y-sm max-h-80 overflow-auto">
            {(overview?.actions ?? []).map((action) => (
              <ActionItem key={action.id} action={action} />
            ))}
            {(overview?.actions.length ?? 0) === 0 && <EmptyState text="No AI actions recorded." />}
          </div>
        </Panel>
      </section>

      <Panel title="System Logs">
        <div className="space-y-2 font-data-mono text-xs max-h-80 overflow-y-auto">
          {(overview?.logs ?? []).map((log) => (
            <LogRow key={log.id} log={log} />
          ))}
          {(overview?.logs.length ?? 0) === 0 && <EmptyState text="No system logs recorded." />}
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

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="overflow-hidden rounded-lg border border-white/10 bg-surface-container">
      <div className="border-b border-white/10 bg-surface-container-high px-md py-sm">
        <span className="font-label-caps text-label-caps uppercase text-on-surface-variant">{title}</span>
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

function StatusPill({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const color =
    normalized === 'success' || normalized === 'ready'
      ? 'text-tertiary border-tertiary/30 bg-tertiary/10'
      : normalized === 'error' || normalized === 'failed'
        ? 'text-error border-error/30 bg-error/10'
        : 'text-cyan-300 border-cyan-400/30 bg-cyan-400/10';
  return <span className={`inline-flex rounded border px-2 py-0.5 font-data-mono text-[10px] uppercase ${color}`}>{status}</span>;
}

function EmptyState({ text }: { text: string }) {
  return <p className="text-sm text-outline">{text}</p>;
}

function formatDate(value?: string | null) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}
