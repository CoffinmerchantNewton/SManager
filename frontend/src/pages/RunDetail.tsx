import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link, useParams } from 'react-router-dom';
import { agentApi, productsApi, runsApi } from '../services/api';
import type { AgentAction, ForecastProduct, ForecastRunWorkflowStatus } from '../types';

interface RunContext {
  run_id: string;
  generated_at?: string;
  run_dir?: string;
  status?: ForecastRunWorkflowStatus;
  diagnose?: {
    findings?: Array<Record<string, any>>;
  };
  events?: Array<Record<string, any>>;
  logs?: Array<{
    name: string;
    path: string;
    size_bytes: number;
    tail: string[];
  }>;
  product_manifest?: {
    products?: Array<Record<string, any>>;
  };
}

export default function RunDetail() {
  const { runId = '' } = useParams();
  const [context, setContext] = useState<RunContext | null>(null);
  const [products, setProducts] = useState<ForecastProduct[]>([]);
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [selectedLog, setSelectedLog] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const logs = context?.logs ?? [];
  const activeLog = useMemo(() => {
    if (!logs.length) return null;
    return logs.find((item) => item.name === selectedLog) ?? logs[0];
  }, [logs, selectedLog]);

  useEffect(() => {
    if (!runId) return;
    void loadDetail();
  }, [runId]);

  const loadDetail = async () => {
    setBusy('loading');
    setError('');
    try {
      const [contextResponse, productsResponse, actionsResponse] = await Promise.all([
        runsApi.context(runId, { tail: 160, event_limit: 120, max_logs: 12 }),
        productsApi.getAll({ run_id: runId, status: 'ready', limit: 100 }),
        agentApi.actions({ run_id: runId, limit: 50 }),
      ]);
      setContext(contextResponse.data.data);
      setProducts(productsResponse.data as ForecastProduct[]);
      setActions(actionsResponse.data.data.actions ?? []);
      const nextLogs = contextResponse.data.data.logs ?? [];
      setSelectedLog((current) => current || nextLogs[0]?.name || '');
    } catch (err: any) {
      setError(err?.response?.data?.detail?.message || err?.message || 'Failed to load run detail');
    } finally {
      setBusy('');
    }
  };

  const syncProducts = async () => {
    setBusy('sync');
    setError('');
    try {
      await runsApi.syncProducts(runId);
      await loadDetail();
    } catch (err: any) {
      setError(err?.response?.data?.detail?.message || err?.message || 'Failed to sync products');
      setBusy('');
    }
  };

  const workflow = context?.status;
  const findings = context?.diagnose?.findings ?? [];
  const events = context?.events ?? [];
  const manifestProducts = context?.product_manifest?.products ?? [];

  return (
    <div className="p-lg technical-grid min-h-full flex flex-col gap-gutter">
      <header className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <Link to="/admin/runs" className="inline-flex items-center gap-1 text-xs text-outline hover:text-on-surface">
            <span className="material-symbols-outlined text-sm">arrow_back</span>
            Run Operations
          </Link>
          <h1 className="font-headline-xl text-headline-xl text-on-surface mt-2 break-all">{runId}</h1>
          <p className="text-outline font-body-md">
            Consolidated status, diagnostics, logs, events, products, and Hermes audit trail.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-sm">
          <button
            onClick={loadDetail}
            disabled={!!busy}
            className="px-md py-sm bg-surface-container-high border border-white/10 rounded-lg text-sm text-on-surface hover:bg-white/10 disabled:opacity-40"
          >
            <span className="material-symbols-outlined align-middle mr-2 text-sm">refresh</span>
            {busy === 'loading' ? 'Loading...' : 'Refresh'}
          </button>
          <button
            onClick={syncProducts}
            disabled={!!busy}
            className="px-md py-sm bg-primary-container text-on-primary-container rounded-lg text-sm font-semibold disabled:opacity-40"
          >
            <span className="material-symbols-outlined align-middle mr-2 text-sm">download</span>
            {busy === 'sync' ? 'Syncing...' : 'Sync Products'}
          </button>
        </div>
      </header>

      {error && (
        <div className="rounded-lg border border-error/30 bg-error-container/20 p-md text-sm text-error">{error}</div>
      )}

      <section className="grid grid-cols-1 xl:grid-cols-4 gap-gutter">
        <Metric label="Status" value={workflow?.status ?? '-'} accent={<StatusPill status={workflow?.status ?? 'pending'} />} />
        <Metric label="Progress" value={`${workflow?.progress ?? 0}%`} />
        <Metric label="Events" value={`${events.length}`} />
        <Metric label="Products" value={`${products.length} synced / ${manifestProducts.length} manifest`} />
      </section>

      <section className="grid grid-cols-1 2xl:grid-cols-[1.35fr_0.65fr] gap-gutter">
        <Panel title="Workflow Nodes">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="text-outline border-b border-white/10">
                <tr>
                  <th className="px-sm py-sm text-[10px]">NODE</th>
                  <th className="px-sm py-sm text-[10px]">STATUS</th>
                  <th className="px-sm py-sm text-[10px]">PROGRESS</th>
                  <th className="px-sm py-sm text-[10px]">ATTEMPT</th>
                  <th className="px-sm py-sm text-[10px]">JOB</th>
                  <th className="px-sm py-sm text-[10px]">MESSAGE</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {(workflow?.nodes ?? []).map((node) => (
                  <tr key={node.node} className="hover:bg-white/[0.03]">
                    <td className="px-sm py-sm font-data-mono text-xs text-cyan-300">{node.node}</td>
                    <td className="px-sm py-sm"><StatusPill status={node.status} /></td>
                    <td className="px-sm py-sm text-xs text-on-surface">{node.progress}%</td>
                    <td className="px-sm py-sm text-xs text-outline">{node.attempt}</td>
                    <td className="px-sm py-sm text-xs text-outline">{node.slurm_job_id || '-'}</td>
                    <td className="px-sm py-sm text-xs text-on-surface-variant">{node.message || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(workflow?.nodes?.length ?? 0) === 0 && <EmptyState text="No workflow nodes loaded." />}
          </div>
        </Panel>

        <Panel title="Diagnostics">
          <div className="space-y-sm max-h-[420px] overflow-auto">
            {findings.map((finding, index) => (
              <div key={`${finding.node ?? 'run'}-${finding.code ?? index}`} className="rounded border border-white/10 bg-surface-container-low p-sm">
                <div className="flex items-center justify-between gap-sm">
                  <span className="font-data-mono text-xs text-cyan-300">{finding.node ?? 'run'}</span>
                  <StatusPill status={String(finding.code ?? finding.level ?? 'finding')} />
                </div>
                <p className="mt-xs text-xs text-on-surface-variant">{finding.message ?? '-'}</p>
                <p className="mt-xs text-[10px] text-outline">Action: {finding.suggested_action ?? 'inspect_context'}</p>
              </div>
            ))}
            {findings.length === 0 && <EmptyState text="No diagnostic findings." />}
          </div>
        </Panel>
      </section>

      <section className="grid grid-cols-1 2xl:grid-cols-[0.7fr_1.3fr] gap-gutter">
        <Panel title="Log Tails">
          <div className="flex flex-wrap gap-xs mb-sm">
            {logs.map((log) => (
              <button
                key={log.name}
                onClick={() => setSelectedLog(log.name)}
                className={`px-2 py-1 rounded border text-[10px] font-data-mono ${
                  activeLog?.name === log.name
                    ? 'border-cyan-400/40 bg-cyan-400/10 text-cyan-300'
                    : 'border-white/10 bg-surface-container-low text-outline'
                }`}
              >
                {log.name}
              </button>
            ))}
          </div>
          <pre className="h-80 overflow-auto whitespace-pre-wrap rounded border border-white/10 bg-black/20 p-sm text-xs text-on-surface-variant">
            {activeLog?.tail?.join('\n') || 'No log tail collected.'}
          </pre>
        </Panel>

        <Panel title="Recent Events">
          <div className="max-h-[380px] overflow-auto divide-y divide-white/5">
            {events.map((event, index) => (
              <div key={`${event.created_at ?? 'event'}-${event.event_type ?? 'event'}-${event.node ?? 'run'}-${index}`} className="py-sm">
                <div className="flex flex-wrap items-center justify-between gap-sm">
                  <span className="font-data-mono text-xs text-cyan-300">{event.event_type ?? 'event'}</span>
                  <span className="text-[10px] text-outline">{event.created_at ?? '-'}</span>
                </div>
                <p className="mt-xs text-xs text-on-surface-variant">{event.message ?? '-'}</p>
                <p className="mt-xs text-[10px] text-outline">{event.node ?? 'run'} / {event.level ?? 'info'}</p>
              </div>
            ))}
            {events.length === 0 && <EmptyState text="No events collected." />}
          </div>
        </Panel>
      </section>

      <section className="grid grid-cols-1 2xl:grid-cols-2 gap-gutter">
        <Panel title="Synced Products">
          <div className="space-y-sm max-h-96 overflow-auto">
            {products.map((product) => (
              <div key={product.id} className="flex items-center justify-between gap-sm rounded border border-white/10 bg-surface-container-low p-sm">
                <div className="min-w-0">
                  <p className="truncate font-data-mono text-xs text-cyan-300">{product.product_name}</p>
                  <p className="text-[10px] text-outline">{product.product_type} / {product.pollen_type} / {product.resolution}</p>
                </div>
                <a
                  href={productsApi.downloadUrl(product.id)}
                  className="inline-flex items-center gap-1 rounded bg-primary-container px-2 py-1 text-[10px] font-semibold text-on-primary-container"
                >
                  <span className="material-symbols-outlined text-sm">download</span>
                  Download
                </a>
              </div>
            ))}
            {products.length === 0 && <EmptyState text="No products synced into the jumpbox database." />}
          </div>
        </Panel>

        <Panel title="Hermes Actions">
          <div className="space-y-sm max-h-96 overflow-auto">
            {actions.map((action) => (
              <div key={action.id} className="rounded border border-white/10 bg-surface-container-low p-sm">
                <div className="flex items-center justify-between gap-sm">
                  <span className="font-data-mono text-xs text-cyan-300">{action.action_type}</span>
                  <StatusPill status={action.status} />
                </div>
                <p className="mt-xs text-xs text-on-surface-variant">{action.reason || '-'}</p>
                <p className="mt-xs text-[10px] text-outline">{action.created_at || '-'}</p>
              </div>
            ))}
            {actions.length === 0 && <EmptyState text="No agent actions recorded." />}
          </div>
        </Panel>
      </section>
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

function Metric({ label, value, accent }: { label: string; value: string; accent?: ReactNode }) {
  return (
    <div className="rounded-lg border border-white/10 bg-surface-container p-md">
      <p className="font-label-caps text-[10px] uppercase text-outline">{label}</p>
      <div className="mt-xs flex items-center justify-between gap-sm">
        <p className="truncate font-data-mono text-lg text-on-surface">{value}</p>
        {accent}
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const color =
    normalized === 'success' || normalized === 'ready'
      ? 'text-tertiary border-tertiary/30 bg-tertiary/10'
      : normalized === 'error' || normalized.includes('missing') || normalized.includes('bad')
        ? 'text-error border-error/30 bg-error/10'
        : 'text-cyan-300 border-cyan-400/30 bg-cyan-400/10';
  return <span className={`inline-flex rounded border px-2 py-0.5 font-data-mono text-[10px] uppercase ${color}`}>{status}</span>;
}

function EmptyState({ text }: { text: string }) {
  return <p className="text-sm text-outline">{text}</p>;
}
