import { useEffect, useMemo, useState } from 'react';
import { agentApi, runsApi } from '../services/api';
import type { AgentAction, ForecastRunWorkflowStatus } from '../types';

const NODE_ORDER = [
  'fnl_verify',
  'wps_geogrid',
  'wps_ungrib',
  'wps_metgrid',
  'wrf_setup',
  'real',
  'compute_gdd',
  'prep_pollen',
  'wrf_run',
  'postprocess_eval',
  'product_extract',
  'package_products',
];

export default function RunOperations() {
  const [form, setForm] = useState({
    run_id: '',
    start: '2026060400',
    end: '2026060412',
    period: 'spring',
    domain: 'neimeng',
    variant: 'official',
    commands_file: '',
  });
  const [runId, setRunId] = useState('');
  const [workflow, setWorkflow] = useState<ForecastRunWorkflowStatus | null>(null);
  const [logs, setLogs] = useState('');
  const [selectedNode, setSelectedNode] = useState('fnl_verify');
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [diagnosis, setDiagnosis] = useState<any | null>(null);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState<{ kind: 'info' | 'error'; text: string } | null>(null);

  const activeRunId = runId || workflow?.run_id || form.run_id;
  const sortedNodes = useMemo(() => {
    const nodes = workflow?.nodes ?? [];
    return [...nodes].sort((a, b) => NODE_ORDER.indexOf(a.node) - NODE_ORDER.indexOf(b.node));
  }, [workflow]);

  useEffect(() => {
    if (activeRunId) {
      loadActions(activeRunId);
    }
  }, [activeRunId]);

  const updateForm = (key: string, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const runAction = async (label: string, action: () => Promise<void>) => {
    setBusy(label);
    setMessage(null);
    try {
      await action();
    } catch (error: any) {
      setMessage({
        kind: 'error',
        text: error?.response?.data?.detail?.message || error?.message || 'Operation failed',
      });
    } finally {
      setBusy('');
    }
  };

  const planRun = () =>
    runAction('Planning run', async () => {
      const payload = {
        ...form,
        run_id: form.run_id || undefined,
        commands_file: form.commands_file || undefined,
      };
      const response = await runsApi.plan(payload);
      const plannedRunId = response.data.data.run_id;
      setRunId(plannedRunId);
      setMessage({ kind: 'info', text: `Run planned: ${plannedRunId}` });
      await refreshStatus(plannedRunId);
    });

  const refreshStatus = async (id = activeRunId) => {
    if (!id) return;
    const response = await runsApi.status(id);
    setWorkflow(response.data.data);
  };

  const verifyFnl = () =>
    runAction('Verifying FNL', async () => {
      if (!activeRunId) return;
      await runsApi.fnlVerify(activeRunId);
      await refreshStatus(activeRunId);
      await loadActions(activeRunId);
    });

  const repairFnl = () =>
    runAction('Repairing FNL', async () => {
      if (!activeRunId) return;
      await agentApi.tick({
        ...form,
        run_id: activeRunId,
        commands_file: form.commands_file || undefined,
        repair_fnl: true,
        dry_run_submit: true,
        allow_noop: true,
      });
      await refreshStatus(activeRunId);
      await loadActions(activeRunId);
    });

  const submitDryRun = () =>
    runAction('Submitting dry-run', async () => {
      if (!activeRunId) return;
      await runsApi.submit(activeRunId, { dry_run: true, allow_noop: true });
      await refreshStatus(activeRunId);
    });

  const syncProducts = () =>
    runAction('Syncing products', async () => {
      if (!activeRunId) return;
      await runsApi.syncProducts(activeRunId);
      await loadActions(activeRunId);
    });

  const loadLogs = () =>
    runAction('Loading logs', async () => {
      if (!activeRunId) return;
      const response = await runsApi.logs(activeRunId, { node: selectedNode, tail: 200 });
      setLogs(response.data.logs);
    });

  const diagnoseRun = () =>
    runAction('Diagnosing run', async () => {
      if (!activeRunId) return;
      const response = await runsApi.diagnose(activeRunId);
      setDiagnosis(response.data.data);
    });

  const retrySelectedNode = (dryRun: boolean) =>
    runAction(dryRun ? 'Retry Dry-run' : 'Retry Real', async () => {
      if (!activeRunId || !selectedNode) return;
      if (!dryRun && !confirm(`Retry node ${selectedNode} for ${activeRunId}?`)) {
        return;
      }
      const response = await runsApi.retry(activeRunId, { node: selectedNode, dry_run: dryRun });
      setMessage({
        kind: 'info',
        text: dryRun
          ? `Retry dry-run checked for ${selectedNode}.`
          : response.data.data?.message || `Retry submitted for ${selectedNode}.`,
      });
      await refreshStatus(activeRunId);
    });

  const cancelRun = (dryRun: boolean) =>
    runAction(dryRun ? 'Cancel Dry-run' : 'Cancel Real', async () => {
      if (!activeRunId) return;
      if (!dryRun && !confirm(`Cancel run ${activeRunId}?`)) {
        return;
      }
      const response = await runsApi.cancel(activeRunId, { dry_run: dryRun });
      const data = response.data.data;
      setMessage({
        kind: 'info',
        text: dryRun
          ? `Cancel dry-run found ${(data.nodes ?? []).length} active nodes.`
          : data.no_op
            ? 'No active nodes to cancel.'
            : `Cancel requested for ${(data.cancelled_nodes ?? []).length} nodes.`,
      });
      await refreshStatus(activeRunId);
    });

  const loadActions = async (id: string) => {
    const response = await agentApi.actions({ run_id: id, limit: 20 });
    setActions(response.data.data.actions ?? []);
  };

  return (
    <div className="p-lg technical-grid min-h-full flex flex-col gap-gutter">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-headline-xl text-headline-xl text-on-surface">Run Operations</h1>
          <p className="text-outline font-body-md">
            Control server-side WRF-Pollen flow, FNL repair, Slurm dry-runs, and Hermes audit state.
          </p>
        </div>
        <button
          onClick={() => refreshStatus()}
          disabled={!activeRunId || !!busy}
          className="px-md py-sm bg-surface-container-high border border-white/10 rounded-lg text-sm text-on-surface hover:bg-white/10 disabled:opacity-40"
        >
          <span className="material-symbols-outlined align-middle mr-2 text-sm">refresh</span>
          Refresh
        </button>
      </header>

      <section className="grid grid-cols-1 xl:grid-cols-[420px_1fr] gap-gutter">
        <div className="bg-surface-container border border-white/10 rounded-lg p-md flex flex-col gap-sm">
          <span className="font-label-caps text-label-caps text-outline uppercase">Run Spec</span>
          <input className="ops-input" placeholder="run_id optional" value={form.run_id} onChange={(e) => updateForm('run_id', e.target.value)} />
          <div className="grid grid-cols-2 gap-sm">
            <input className="ops-input" value={form.start} onChange={(e) => updateForm('start', e.target.value)} />
            <input className="ops-input" value={form.end} onChange={(e) => updateForm('end', e.target.value)} />
          </div>
          <div className="grid grid-cols-3 gap-sm">
            <select className="ops-input" value={form.period} onChange={(e) => updateForm('period', e.target.value)}>
              <option value="spring">spring</option>
              <option value="summer">summer</option>
              <option value="autumn">autumn</option>
            </select>
            <input className="ops-input" value={form.domain} onChange={(e) => updateForm('domain', e.target.value)} />
            <input className="ops-input" value={form.variant} onChange={(e) => updateForm('variant', e.target.value)} />
          </div>
          <input
            className="ops-input"
            placeholder="server commands-file path"
            value={form.commands_file}
            onChange={(e) => updateForm('commands_file', e.target.value)}
          />
          <div className="grid grid-cols-2 gap-sm pt-sm">
            <OpsButton label="Plan" icon="add_task" busy={busy} onClick={planRun} />
            <OpsButton label="FNL Verify" icon="fact_check" busy={busy} disabled={!activeRunId} onClick={verifyFnl} />
            <OpsButton label="Hermes Repair" icon="build" busy={busy} disabled={!activeRunId} onClick={repairFnl} />
            <OpsButton label="Submit Dry-run" icon="send" busy={busy} disabled={!activeRunId} onClick={submitDryRun} />
            <OpsButton label="Sync Products" icon="download" busy={busy} disabled={!activeRunId} onClick={syncProducts} />
            <OpsButton label="Load Logs" icon="article" busy={busy} disabled={!activeRunId} onClick={loadLogs} />
            <OpsButton label="Diagnose" icon="troubleshoot" busy={busy} disabled={!activeRunId} onClick={diagnoseRun} />
            <OpsButton label="Retry Dry-run" icon="restart_alt" busy={busy} disabled={!activeRunId || !selectedNode} onClick={() => retrySelectedNode(true)} />
            <OpsButton label="Retry Real" icon="published_with_changes" busy={busy} disabled={!activeRunId || !selectedNode} onClick={() => retrySelectedNode(false)} tone="danger" />
            <OpsButton label="Cancel Dry-run" icon="block" busy={busy} disabled={!activeRunId} onClick={() => cancelRun(true)} />
            <OpsButton label="Cancel Real" icon="dangerous" busy={busy} disabled={!activeRunId} onClick={() => cancelRun(false)} tone="danger" />
          </div>
          {message && (
            <div
              className={`text-xs rounded p-sm border ${
                message.kind === 'error'
                  ? 'text-error bg-error-container/20 border-error/20'
                  : 'text-on-surface-variant bg-surface-container-low border-white/10'
              }`}
            >
              {message.text}
            </div>
          )}
        </div>

        <div className="bg-surface-container border border-white/10 rounded-lg overflow-hidden">
          <div className="px-md py-sm bg-surface-container-high border-b border-white/10 flex items-center justify-between">
            <span className="font-label-caps text-label-caps text-on-surface-variant">Workflow Status</span>
            <StatusPill status={workflow?.status ?? 'pending'} />
          </div>
          <div className="p-md">
            <div className="grid grid-cols-3 gap-gutter mb-md">
              <Metric label="RUN ID" value={workflow?.run_id || activeRunId || '-'} />
              <Metric label="PROGRESS" value={`${workflow?.progress ?? 0}%`} />
              <Metric label="UPDATED" value={workflow?.updated_at ? new Date(workflow.updated_at).toLocaleString() : '-'} />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="text-outline border-b border-white/10">
                  <tr>
                    <th className="px-sm py-sm text-[10px]">NODE</th>
                    <th className="px-sm py-sm text-[10px]">STATUS</th>
                    <th className="px-sm py-sm text-[10px]">PROGRESS</th>
                    <th className="px-sm py-sm text-[10px]">JOB</th>
                    <th className="px-sm py-sm text-[10px]">MESSAGE</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {sortedNodes.map((node) => (
                    <tr
                      key={node.node}
                      onClick={() => setSelectedNode(node.node)}
                      className={`cursor-pointer hover:bg-white/[0.03] ${selectedNode === node.node ? 'bg-cyan-400/5' : ''}`}
                    >
                      <td className="px-sm py-sm font-data-mono text-xs text-cyan-300">{node.node}</td>
                      <td className="px-sm py-sm"><StatusPill status={node.status} /></td>
                      <td className="px-sm py-sm text-xs text-on-surface">{node.progress}%</td>
                      <td className="px-sm py-sm text-xs text-outline">{node.slurm_job_id || '-'}</td>
                      <td className="px-sm py-sm text-xs text-on-surface-variant">{node.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-gutter">
        <div className="bg-surface-container border border-white/10 rounded-lg overflow-hidden">
          <div className="px-md py-sm bg-surface-container-high border-b border-white/10">
            <span className="font-label-caps text-label-caps text-on-surface-variant">Node Logs: {selectedNode}</span>
          </div>
          <pre className="p-md h-72 overflow-auto text-xs font-data-mono text-on-surface-variant whitespace-pre-wrap">{logs || 'No logs loaded.'}</pre>
        </div>
        <div className="bg-surface-container border border-white/10 rounded-lg overflow-hidden">
          <div className="px-md py-sm bg-surface-container-high border-b border-white/10">
            <span className="font-label-caps text-label-caps text-on-surface-variant">Diagnostics</span>
          </div>
          <div className="p-md space-y-sm h-72 overflow-auto">
            {diagnosis?.findings?.map((finding: any, index: number) => (
              <div key={`${finding.node || 'run'}-${finding.code || index}`} className="border border-white/10 rounded p-sm bg-surface-container-low">
                <div className="flex items-center justify-between gap-sm">
                  <span className="font-data-mono text-xs text-cyan-300">{finding.node || 'run'}</span>
                  <StatusPill status={finding.code || 'finding'} />
                </div>
                <p className="text-xs text-on-surface-variant mt-xs">{finding.message || '-'}</p>
                <p className="text-[10px] text-outline mt-xs">Action: {finding.suggested_action || 'inspect_logs'}</p>
              </div>
            ))}
            {diagnosis && (diagnosis.findings?.length ?? 0) === 0 && (
              <p className="text-sm text-outline">No findings reported for this run.</p>
            )}
            {!diagnosis && <p className="text-sm text-outline">No diagnostics loaded.</p>}
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-gutter">
        <div className="bg-surface-container border border-white/10 rounded-lg overflow-hidden">
          <div className="px-md py-sm bg-surface-container-high border-b border-white/10">
            <span className="font-label-caps text-label-caps text-on-surface-variant">Hermes Actions</span>
          </div>
          <div className="p-md space-y-sm h-72 overflow-auto">
            {actions.map((action) => (
              <div key={action.id} className="border border-white/10 rounded p-sm bg-surface-container-low">
                <div className="flex items-center justify-between">
                  <span className="font-data-mono text-xs text-cyan-300">{action.action_type}</span>
                  <StatusPill status={action.status} />
                </div>
                <p className="text-xs text-outline mt-xs">{action.reason || '-'}</p>
              </div>
            ))}
            {actions.length === 0 && <p className="text-sm text-outline">No actions recorded.</p>}
          </div>
        </div>
      </section>
    </div>
  );
}

function OpsButton({
  label,
  icon,
  busy,
  disabled,
  onClick,
  tone = 'primary',
}: {
  label: string;
  icon: string;
  busy: string;
  disabled?: boolean;
  onClick: () => void;
  tone?: 'primary' | 'danger';
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || !!busy}
      className={`px-sm py-sm rounded-lg text-xs font-semibold flex items-center justify-center gap-2 disabled:opacity-40 ${
        tone === 'danger'
          ? 'bg-error-container/30 text-error border border-error/30 hover:bg-error-container/40'
          : 'bg-primary-container text-on-primary-container hover:shadow-[0_0_12px_rgba(0,102,255,0.25)]'
      }`}
    >
      <span className="material-symbols-outlined text-sm">{icon}</span>
      {busy === label ? 'Working...' : label}
    </button>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-surface-container-low border border-white/10 rounded p-sm">
      <p className="font-label-caps text-[10px] text-outline">{label}</p>
      <p className="font-data-mono text-sm text-on-surface truncate">{value}</p>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const color = status === 'success' || status === 'server_ok' ? 'text-tertiary border-tertiary/30 bg-tertiary/10' : status === 'error' || status.includes('bad') || status === 'missing' ? 'text-error border-error/30 bg-error/10' : 'text-cyan-300 border-cyan-400/30 bg-cyan-400/10';
  return <span className={`inline-flex px-2 py-0.5 rounded border text-[10px] uppercase font-data-mono ${color}`}>{status}</span>;
}
