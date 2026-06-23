import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useParams } from 'react-router-dom';
import { StatusPill } from '../components/RunDisplay';
import { useI18n } from '../i18n';
import { useRunBackNavigation } from '../hooks/useRunNavigation';
import { buildRunKey, productsApi, runsApi } from '../services/api';
import type { ForecastProduct, ForecastRunWorkflowStatus, RunStateJson } from '../types';
import { errorMessage } from '../utils/errors';

const PIPELINE_STAGES = [
  'geogrid',
  'linkgrib',
  'ungrib',
  'metgrid',
  'real',
  'wrfchemi',
  'wrf',
  'postprocess',
] as const;

interface RunContext {
  run_id: string;
  generated_at?: string;
  run_dir?: string;
  status?: ForecastRunWorkflowStatus;
  state?: RunStateJson;
  effective_state?: Record<string, string>;
  failure?: RunStateJson['failure'];
  anomalies?: string[];
  slurm_jobs?: Array<{ job_id: string; name: string; state: string; time?: string }>;
  diagnose?: {
    findings?: JsonRecord[];
  };
  events?: JsonRecord[];
  logs?: Array<{
    name: string;
    path: string;
    size_bytes: number;
    tail: string[];
  }>;
  stale?: boolean;
}

type JsonRecord = Record<string, unknown>;

export default function RunDetail() {
  const { t } = useI18n();
  const { season = '', region = '', runId = '' } = useParams();
  const { goBack, backLabel } = useRunBackNavigation('/admin/dashboard', t('back'));
  const runKey = buildRunKey(season, region, runId);
  const [context, setContext] = useState<RunContext | null>(null);
  const [products, setProducts] = useState<ForecastProduct[]>([]);
  const [selectedLog, setSelectedLog] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const logs = useMemo(() => context?.logs ?? [], [context?.logs]);
  const activeLog = useMemo(() => {
    if (!logs.length) return null;
    return logs.find((item) => item.name === selectedLog) ?? logs[0];
  }, [logs, selectedLog]);

  const loadDetail = useCallback(async () => {
    if (!runKey || runKey.includes('//')) return;
    setBusy('loading');
    setError('');
    try {
      const [contextResponse, productsResponse, diagnoseResponse] = await Promise.all([
        runsApi.context(runKey, { tail: 160 }),
        runsApi.products(runKey),
        runsApi.diagnose(runKey),
      ]);
      const data = contextResponse.data.data;
      setContext({
        ...data,
        diagnose: diagnoseResponse.data.data,
      });
      setProducts(productsResponse.data.data.products ?? []);
      const nextLogs = data.logs ?? [];
      setSelectedLog((current) => current || nextLogs[0]?.name || '');
    } catch (err: unknown) {
      setError(errorMessage(err, 'Failed to load run detail'));
    } finally {
      setBusy('');
    }
  }, [runKey]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  const pipelineStages = useMemo(() => {
    const effective = context?.effective_state ?? {};
    const raw = context?.state;
    const steps = raw?.steps ?? {};

    return PIPELINE_STAGES.map((stage) => {
      const stepEntry = steps[stage];
      const stepDetail =
        stepEntry && typeof stepEntry === 'object' ? stepEntry : undefined;
      const status = effective[stage] ?? (typeof stepEntry === 'string' ? stepEntry : stepEntry?.status) ?? 'pending';
      return {
        stage,
        status,
        started_at: stepDetail?.started_at,
        finished_at: stepDetail?.finished_at,
      };
    });
  }, [context?.effective_state, context?.state]);

  const failureText = useMemo(() => {
    const failure = context?.failure ?? context?.state?.failure;
    if (!failure) return null;
    if (typeof failure === 'string') return failure;
    const parts = [
      failure.step || failure.stage,
      failure.message || failure.error,
    ].filter(Boolean);
    return parts.join(': ');
  }, [context?.failure, context?.state?.failure]);

  const workflow = context?.status;
  const findings = context?.diagnose?.findings ?? [];

  return (
    <div className="p-lg technical-grid min-h-full flex flex-col gap-gutter">
      <header className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <button
            type="button"
            onClick={goBack}
            className="inline-flex items-center gap-1 text-xs text-outline hover:text-on-surface"
          >
            <span className="material-symbols-outlined text-sm">arrow_back</span>
            {backLabel}
          </button>
          <h1 className="font-headline-xl text-headline-xl text-on-surface mt-2 break-all">{runKey}</h1>
          <p className="text-outline font-body-md">{t('runDetailSubtitle')}</p>
          {context?.stale && context?.error && (
            <p className="mt-1 text-xs text-amber-300">数据来自本地缓存（服务器暂不可达）</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-sm">
          <button
            onClick={loadDetail}
            disabled={!!busy}
            className="px-md py-sm bg-surface-container-high border border-white/10 rounded-lg text-sm text-on-surface hover:bg-white/10 disabled:opacity-40"
          >
            <span className="material-symbols-outlined align-middle mr-2 text-sm">refresh</span>
            {busy === 'loading' ? `${t('loading')}...` : t('refresh')}
          </button>
        </div>
      </header>

      {error && (
        <div className="rounded-lg border border-error/30 bg-error-container/20 p-md text-sm text-error">{error}</div>
      )}

      <section className="grid grid-cols-1 xl:grid-cols-4 gap-gutter">
        <Metric label={t('status')} value={workflow?.status ?? '-'} accent={<StatusPill status={workflow?.status ?? 'pending'} />} />
        <Metric label={t('progress')} value={`${workflow?.progress ?? 0}%`} />
        <Metric label={t('domain')} value={region || '-'} />
        <Metric label="Slurm 活跃" value={`${context?.slurm_jobs?.filter((j) => ['RUNNING', 'PENDING', 'CONFIGURING'].includes((j.state || '').toUpperCase())).length ?? 0}`} />
      </section>

      {(context?.slurm_jobs?.length ?? 0) > 0 && (
        <Panel title="Slurm 任务">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="border-b border-white/10 text-outline">
                <tr>
                  <th className="px-sm py-sm text-[10px]">Job ID</th>
                  <th className="px-sm py-sm text-[10px]">Name</th>
                  <th className="px-sm py-sm text-[10px]">{t('status')}</th>
                  <th className="px-sm py-sm text-[10px]">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {context?.slurm_jobs?.map((job) => (
                  <tr key={job.job_id} className="hover:bg-white/[0.03]">
                    <td className="px-sm py-sm font-data-mono text-xs text-cyan-300">{job.job_id}</td>
                    <td className="px-sm py-sm text-xs text-on-surface">{job.name}</td>
                    <td className="px-sm py-sm"><StatusPill status={job.state} /></td>
                    <td className="px-sm py-sm text-xs text-outline">{job.time || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      <Panel title="Pipeline State">
        {context?.state?.updated_at && (
          <p className="mb-sm text-[10px] text-outline">state.json 更新于 {context.state.updated_at}</p>
        )}
        {failureText && (
          <div className="mb-md rounded border border-error/30 bg-error-container/10 p-sm text-xs text-error">
            failure: {failureText}
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="border-b border-white/10 text-outline">
              <tr>
                <th className="px-sm py-sm text-[10px]">Stage</th>
                <th className="px-sm py-sm text-[10px]">{t('status')}</th>
                <th className="px-sm py-sm text-[10px]">Started</th>
                <th className="px-sm py-sm text-[10px]">Finished</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {pipelineStages.map((item) => (
                <tr key={item.stage} className="hover:bg-white/[0.03]">
                  <td className="px-sm py-sm font-data-mono text-xs text-cyan-300">{item.stage}</td>
                  <td className="px-sm py-sm"><StatusPill status={item.status} /></td>
                  <td className="px-sm py-sm text-xs text-outline">{item.started_at || '-'}</td>
                  <td className="px-sm py-sm text-xs text-outline">{item.finished_at || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {pipelineStages.every((item) => item.status === 'pending') && !context?.state && (
          <EmptyState text="No state.json stages yet." />
        )}
        {(context?.anomalies?.length ?? 0) > 0 && (
          <div className="mt-md space-y-xs rounded border border-error/30 bg-error-container/10 p-sm">
            <p className="text-[10px] font-semibold uppercase text-error">Reconcile 异常</p>
            {(context?.anomalies ?? []).map((item) => (
              <p key={item} className="text-xs text-on-surface-variant">{item}</p>
            ))}
          </div>
        )}
      </Panel>

      <section className="grid grid-cols-1 2xl:grid-cols-[1.35fr_0.65fr] gap-gutter">
        <Panel title={t('workflowNodes')}>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="text-outline border-b border-white/10">
                <tr>
                  <th className="px-sm py-sm text-[10px]">{t('node')}</th>
                  <th className="px-sm py-sm text-[10px]">{t('status')}</th>
                  <th className="px-sm py-sm text-[10px]">{t('progress')}</th>
                  <th className="px-sm py-sm text-[10px]">Started</th>
                  <th className="px-sm py-sm text-[10px]">Finished</th>
                  <th className="px-sm py-sm text-[10px]">{t('job')}</th>
                  <th className="px-sm py-sm text-[10px]">{t('message')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {(workflow?.nodes ?? []).map((node) => (
                  <tr key={node.node} className="hover:bg-white/[0.03]">
                    <td className="px-sm py-sm font-data-mono text-xs text-cyan-300">{node.node}</td>
                    <td className="px-sm py-sm"><StatusPill status={node.status} /></td>
                    <td className="px-sm py-sm text-xs text-on-surface">{node.progress}%</td>
                    <td className="px-sm py-sm text-xs text-outline">{node.started_at || '-'}</td>
                    <td className="px-sm py-sm text-xs text-outline">{node.finished_at || '-'}</td>
                    <td className="px-sm py-sm text-xs text-outline">{node.slurm_job_id || '-'}{node.slurm_state ? ` (${node.slurm_state})` : ''}</td>
                    <td className="px-sm py-sm text-xs text-on-surface-variant">{node.message || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(workflow?.nodes?.length ?? 0) === 0 && <EmptyState text={t('noWorkflowNodes')} />}
          </div>
        </Panel>

        <Panel title={t('diagnostics')}>
          <div className="space-y-sm max-h-[420px] overflow-auto">
            {findings.map((finding, index) => (
              <div key={`${finding.node ?? 'run'}-${finding.code ?? index}`} className="rounded border border-white/10 bg-surface-container-low p-sm">
                <div className="flex items-center justify-between gap-sm">
                  <span className="font-data-mono text-xs text-cyan-300">{String(finding.node ?? 'run')}</span>
                  <StatusPill status={String(finding.code ?? finding.level ?? 'finding')} />
                </div>
                <p className="mt-xs text-xs text-on-surface-variant">{String(finding.message ?? '-')}</p>
              </div>
            ))}
            {findings.length === 0 && <EmptyState text={t('noDiagnosticFindings')} />}
          </div>
        </Panel>
      </section>

      <section className="grid grid-cols-1 2xl:grid-cols-[0.7fr_1.3fr] gap-gutter">
        <Panel title={t('logTails')}>
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
            {activeLog?.tail?.join('\n') || t('noLogTail')}
          </pre>
          <p className="mt-sm break-all text-[10px] text-outline">{context?.run_dir || '-'}</p>
        </Panel>

        <Panel title="Slurm Jobs">
          <div className="space-y-sm">
            {(context?.slurm_jobs ?? []).map((job) => (
              <div key={job.job_id} className="rounded border border-white/10 bg-surface-container-low p-sm">
                <div className="flex items-center justify-between gap-sm">
                  <span className="font-data-mono text-xs text-cyan-300">{job.job_id}</span>
                  <StatusPill status={job.state} />
                </div>
                <p className="mt-xs text-xs text-outline">{job.name}</p>
                <p className="mt-xs text-[10px] text-on-surface-variant">{job.time || '-'}</p>
              </div>
            ))}
            {(context?.slurm_jobs?.length ?? 0) === 0 && <EmptyState text="No matching Slurm jobs." />}
          </div>
        </Panel>
      </section>

      <Panel title={t('syncedProducts')}>
        <div className="space-y-sm max-h-96 overflow-auto">
          {products.map((product) => (
            <div key={product.id} className="flex items-center justify-between gap-sm rounded border border-white/10 bg-surface-container-low p-sm">
              <div className="min-w-0">
                <p className="truncate font-data-mono text-xs text-cyan-300">{product.product_name}</p>
                <p className="text-[10px] text-outline">{product.product_type} / {product.pollen_type} / {product.resolution}</p>
              </div>
              {product.id ? (
                <a
                  href={productsApi.downloadUrl(product.id)}
                  className="inline-flex items-center gap-1 rounded bg-primary-container px-2 py-1 text-[10px] font-semibold text-on-primary-container"
                >
                  {t('download')}
                </a>
              ) : null}
            </div>
          ))}
          {products.length === 0 && <EmptyState text={t('noSyncedDbProducts')} />}
        </div>
      </Panel>
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

function EmptyState({ text }: { text: string }) {
  return <p className="text-sm text-outline">{text}</p>;
}
