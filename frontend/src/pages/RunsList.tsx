import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { SlurmSummary, StatusPill } from '../components/RunDisplay';
import { useI18n } from '../i18n';
import { runNavState } from '../hooks/useRunNavigation';
import { runDetailPath, runsApi } from '../services/api';
import type { DashboardRunSummary } from '../types';
import { errorMessage } from '../utils/errors';

type RunRow = DashboardRunSummary & {
  run_key?: string;
  season?: string;
  region?: string;
  start_date?: string;
  anomalies?: string[];
};

const STATUS_OPTIONS = ['', 'running', 'pending', 'ready', 'success', 'error'];

export default function RunsList() {
  const { t } = useI18n();
  const location = useLocation();
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [stale, setStale] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');
  const [limit, setLimit] = useState(200);

  const loadRuns = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params: Record<string, string | number> = { limit };
      if (statusFilter) params.status = statusFilter;
      const response = await runsApi.list(params);
      const data = response.data?.data;
      setRuns((data?.runs ?? []) as RunRow[]);
      setStale(Boolean(data?.stale));
    } catch (err: unknown) {
      setError(errorMessage(err, '加载运行列表失败'));
    } finally {
      setLoading(false);
    }
  }, [limit, statusFilter]);

  useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  const navFrom = useMemo(() => runNavState(location.pathname, t('allRunsTitle')), [location.pathname, t]);

  return (
    <div className="min-h-full p-lg technical-grid flex flex-col gap-gutter">
      <header className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <Link
            to="/admin/dashboard"
            className="inline-flex items-center gap-1 text-xs text-outline hover:text-on-surface"
          >
            <span className="material-symbols-outlined text-sm">arrow_back</span>
            {t('backToDashboard')}
          </Link>
          <h1 className="mt-2 font-headline-xl text-headline-xl text-on-surface">{t('allRunsTitle')}</h1>
          <p className="font-body-md text-outline">{t('allRunsSubtitle')}</p>
          {stale && <p className="mt-2 text-xs text-amber-300">服务器暂不可达，展示缓存数据。</p>}
        </div>
        <button
          onClick={() => void loadRuns()}
          disabled={loading}
          className="rounded-lg border border-white/10 bg-surface-container-high px-md py-sm text-sm text-on-surface hover:bg-white/10 disabled:opacity-40"
        >
          <span className="material-symbols-outlined mr-2 align-middle text-sm">refresh</span>
          {t('refresh')}
        </button>
      </header>

      <div className="flex flex-wrap items-end gap-md rounded-lg border border-white/10 bg-surface-container p-md">
        <label className="flex flex-col gap-1 text-xs">
          <span className="text-outline">{t('status')}</span>
          <select
            className="ops-input min-w-[140px]"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">{t('allStatuses')}</option>
            {STATUS_OPTIONS.filter(Boolean).map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span className="text-outline">{t('limit')}</span>
          <select className="ops-input min-w-[120px]" value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
            {[50, 100, 200, 500].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <p className="text-xs text-outline">
          {loading ? t('loading') : `${runs.length} ${t('records')}`}
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-error/30 bg-error-container/20 p-md text-sm text-error">{error}</div>
      )}

      <div className="overflow-hidden rounded-lg border border-white/10 bg-surface-container">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="border-b border-white/10 bg-surface-container-high text-outline">
              <tr>
                <th className="px-sm py-sm text-[10px]">{t('run')}</th>
                <th className="px-sm py-sm text-[10px]">{t('status')}</th>
                <th className="px-sm py-sm text-[10px]">{t('progress')}</th>
                <th className="px-sm py-sm text-[10px]">Slurm</th>
                <th className="px-sm py-sm text-[10px]">{t('season')}</th>
                <th className="px-sm py-sm text-[10px]">{t('domain')}</th>
                <th className="px-sm py-sm text-[10px]">{t('startDate')}</th>
                <th className="px-sm py-sm text-[10px]">{t('notes')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {runs.map((run) => (
                <tr key={run.run_key || `${run.season}-${run.region}-${run.run_id}`} className="hover:bg-white/[0.03]">
                  <td className="max-w-[280px] px-sm py-sm">
                    <Link
                      to={runDetailPath(run)}
                      state={navFrom}
                      className="font-data-mono text-xs text-cyan-300 hover:text-cyan-200"
                    >
                      {run.run_key || run.run_id}
                    </Link>
                  </td>
                  <td className="px-sm py-sm">
                    <StatusPill status={String(run.status)} />
                  </td>
                  <td className="px-sm py-sm text-xs text-on-surface">{run.progress ?? 0}%</td>
                  <td className="px-sm py-sm text-xs">
                    <SlurmSummary run={run} />
                  </td>
                  <td className="px-sm py-sm text-xs text-outline">{run.season || run.period || '-'}</td>
                  <td className="px-sm py-sm text-xs text-outline">{run.region || run.domain || '-'}</td>
                  <td className="px-sm py-sm text-xs text-outline">{run.start_date || run.start_time || '-'}</td>
                  <td className="max-w-[240px] px-sm py-sm text-[10px] text-on-surface-variant">
                    {run.last_error || (run.anomalies?.length ? run.anomalies[0] : '-')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!loading && runs.length === 0 && (
            <p className="p-md text-sm text-outline">{t('noRuns')}</p>
          )}
        </div>
      </div>
    </div>
  );
}
