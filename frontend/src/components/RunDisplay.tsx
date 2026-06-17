import type { DashboardRunSummary } from '../types';

export function StatusPill({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  let color = 'text-outline border-white/10 bg-surface-container-high';
  if (normalized === 'success' || normalized === 'completed') {
    color = 'text-tertiary border-tertiary/30 bg-tertiary/10';
  } else if (normalized === 'running' || normalized === 'retrying') {
    color = 'text-cyan-300 border-cyan-400/30 bg-cyan-400/10';
  } else if (normalized === 'error' || normalized === 'failed' || normalized === 'fail') {
    color = 'text-error border-error/30 bg-error/10';
  } else if (normalized === 'pending' || normalized === 'ready') {
    color = 'text-amber-200 border-amber-400/30 bg-amber-400/10';
  } else if (['failed', 'timeout', 'cancelled', 'deadline'].some((s) => normalized.includes(s))) {
    color = 'text-error border-error/30 bg-error/10';
  }
  return (
    <span className={`inline-flex rounded border px-2 py-0.5 font-data-mono text-[10px] uppercase ${color}`}>
      {status}
    </span>
  );
}

export function SlurmSummary({ run }: { run: DashboardRunSummary }) {
  const jobs = run.slurm_jobs ?? [];
  const active = jobs.filter((job) =>
    ['RUNNING', 'PENDING', 'CONFIGURING'].includes((job.state || '').toUpperCase()),
  );
  if (active.length === 0 && jobs.length === 0) {
    return <span className="text-outline">-</span>;
  }
  const display = (active.length ? active : jobs.slice(0, 3)).map((job) => (
    <span key={job.job_id} className="mr-2 block font-data-mono text-[10px] text-cyan-300">
      {job.job_id} <span className="text-outline">({job.state})</span>
    </span>
  ));
  return <div className="max-w-[240px]">{display}</div>;
}
