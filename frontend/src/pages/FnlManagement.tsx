import { useCallback, useEffect, useState } from 'react';
import { useI18n } from '../i18n';
import { fnlApi } from '../services/api';
import type { FnlFileStatus } from '../types';
import { errorMessage } from '../utils/errors';

export default function FnlManagement() {
  const { t } = useI18n();
  const [query, setQuery] = useState({ start_date: '20260616', status: '' });
  const [files, setFiles] = useState<FnlFileStatus[]>([]);
  const [scanSummary, setScanSummary] = useState<{ missing?: string[]; total?: number; available?: number } | null>(null);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [stale, setStale] = useState(false);

  const updateQuery = (key: string, value: string) => {
    setQuery((current) => ({ ...current, [key]: value }));
  };

  const runAction = useCallback(async (label: string, action: () => Promise<void>) => {
    setBusy(label);
    setMessage('');
    try {
      await action();
    } catch (error: unknown) {
      setMessage(errorMessage(error, 'Operation failed'));
    } finally {
      setBusy('');
    }
  }, []);

  const loadCoverage = useCallback(async () => {
    const params: Record<string, string> = { start: query.start_date };
    if (query.status) params.status = query.status;
    const response = await fnlApi.coverage(params);
    setFiles(response.data.data.files ?? []);
    setScanSummary(response.data.data.scan ?? null);
    setStale(Boolean(response.data.data.stale));
  }, [query.start_date, query.status]);

  const verifyServer = useCallback(() =>
    runAction(t('verifyServer'), async () => {
      const response = await fnlApi.verifyServer({ start: query.start_date });
      setFiles(response.data.data.files ?? []);
      setScanSummary(response.data.data.scan ?? null);
      setMessage(response.data.ok ? 'FNL 扫描完成，无缺失。' : 'FNL 仍有缺口。');
    }), [query.start_date, runAction, t]);

  const repairPending = useCallback(() =>
    runAction(t('repairFnl'), async () => {
      const response = await fnlApi.repair({ use_cache: true });
      const data = response.data.data;
      setMessage(
        `修复完成：成功 ${data.success ?? 0}/${data.total ?? 0}` +
          ((data.failed ?? 0) > 0 ? `，失败 ${data.failed}` : ''),
      );
      await loadCoverage();
    }), [loadCoverage, runAction, t]);

  const repairSingle = useCallback((filename: string) =>
    runAction(filename, async () => {
      const response = await fnlApi.repairOne(filename, { use_cache: true });
      const data = response.data.data;
      setMessage(data.ok ? `${filename} 已修复并归档` : `${filename} 失败：${data.error || 'unknown'}`);
      await loadCoverage();
    }), [loadCoverage, runAction]);

  useEffect(() => {
    void loadCoverage();
  }, [loadCoverage]);

  const okCount = files.filter((file) => !file.needs_repair && !['missing', 'pending', 'expired'].includes(file.status)).length;
  const repairCount = files.filter((file) => file.needs_repair || ['missing', 'pending', 'expired'].includes(file.status)).length;

  return (
    <div className="p-lg technical-grid min-h-full flex flex-col gap-gutter">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-headline-xl text-headline-xl text-on-surface">{t('fnlTitle')}</h1>
          <p className="text-outline font-body-md">{t('fnlSubtitle')}</p>
          {stale && <p className="mt-2 text-xs text-amber-300">服务器暂不可达，展示缓存数据。</p>}
        </div>
        <button
          onClick={() => void loadCoverage()}
          disabled={!!busy}
          className="px-md py-sm bg-surface-container-high border border-white/10 rounded-lg text-sm text-on-surface hover:bg-white/10 disabled:opacity-40"
        >
          <span className="material-symbols-outlined align-middle mr-2 text-sm">refresh</span>
          {t('refresh')}
        </button>
      </header>

      <section className="grid grid-cols-1 xl:grid-cols-[420px_1fr] gap-gutter">
        <div className="bg-surface-container border border-white/10 rounded-lg p-md flex flex-col gap-sm">
          <span className="font-label-caps text-label-caps text-outline uppercase">{t('scanTarget')}</span>
          <input
            className="ops-input"
            placeholder="预报起始日期 YYYYMMDD"
            value={query.start_date}
            onChange={(e) => updateQuery('start_date', e.target.value)}
          />
          <select className="ops-input" value={query.status} onChange={(e) => updateQuery('status', e.target.value)}>
            <option value="">{t('allStatuses')}</option>
            <option value="missing">missing</option>
            <option value="pending">pending</option>
            <option value="staging">staging</option>
            <option value="uploaded">uploaded</option>
            <option value="verified">verified</option>
            <option value="completed">completed</option>
          </select>
          {scanSummary && (
            <div className="rounded border border-white/10 bg-surface-container-low p-sm text-xs text-on-surface-variant">
              FNL 窗口: {scanSummary.available ?? 0}/{scanSummary.total ?? 0} 可用，缺失 {scanSummary.missing?.length ?? 0}
            </div>
          )}
          <div className="grid grid-cols-3 gap-sm py-sm">
            <Metric label={t('files')} value={`${files.length}`} />
            <Metric label={t('ready')} value={`${okCount}`} />
            <Metric label={t('repair')} value={`${repairCount}`} />
          </div>
          <div className="grid grid-cols-2 gap-sm">
            <ActionButton label={t('verifyServer')} icon="travel_explore" busy={busy} workingLabel={t('working')} onClick={verifyServer} />
            <ActionButton label={t('repairFnl')} icon="build" busy={busy} workingLabel={t('working')} onClick={repairPending} />
          </div>
          {message && <div className="text-xs text-on-surface-variant bg-surface-container-low border border-white/10 rounded p-sm">{message}</div>}
        </div>

        <div className="bg-surface-container border border-white/10 rounded-lg overflow-hidden">
          <div className="px-md py-sm bg-surface-container-high border-b border-white/10 flex items-center justify-between">
            <span className="font-label-caps text-label-caps text-on-surface-variant">{t('fnlCoverage')}</span>
            <span className="text-xs text-outline">{files.length} {t('records')}</span>
          </div>
          <div className="overflow-auto max-h-[calc(100vh-14rem)]">
            <table className="w-full text-left">
              <thead className="sticky top-0 bg-surface-container-high text-outline border-b border-white/10">
                <tr>
                  <th className="px-sm py-sm text-[10px]">{t('validTime')}</th>
                  <th className="px-sm py-sm text-[10px]">{t('file')}</th>
                  <th className="px-sm py-sm text-[10px]">{t('status')}</th>
                  <th className="px-sm py-sm text-[10px]">{t('source')}</th>
                  <th className="px-sm py-sm text-[10px]">{t('size')}</th>
                  <th className="px-sm py-sm text-[10px]">区域</th>
                  <th className="px-sm py-sm text-[10px]">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {files.map((file) => (
                  <tr key={`${file.valid_time}-${file.file_name}`} className="hover:bg-white/[0.03]">
                    <td className="px-sm py-sm font-data-mono text-xs text-cyan-300">{file.valid_time || file.date || '-'}</td>
                    <td className="px-sm py-sm text-xs text-on-surface">{file.file_name}</td>
                    <td className="px-sm py-sm"><StatusPill status={file.status} /></td>
                    <td className="px-sm py-sm text-xs text-outline">{file.source || '-'}</td>
                    <td className="px-sm py-sm text-xs text-on-surface-variant">{formatBytes(file.size_bytes)}</td>
                    <td className="px-sm py-sm text-xs text-outline">{file.region || '-'}</td>
                    <td className="px-sm py-sm">
                      {(file.needs_repair || file.status === 'missing' || file.status === 'pending') && file.file_name ? (
                        <button
                          type="button"
                          disabled={!!busy}
                          onClick={() => void repairSingle(file.file_name)}
                          className="rounded bg-primary-container px-2 py-1 text-[10px] font-semibold text-on-primary-container disabled:opacity-40"
                        >
                          修复
                        </button>
                      ) : (
                        <span className="text-[10px] text-outline">-</span>
                      )}
                    </td>
                  </tr>
                ))}
                {files.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-md py-lg text-center text-outline">{t('noFnlRecords')}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

function ActionButton({ label, icon, busy, workingLabel, onClick }: { label: string; icon: string; busy: string; workingLabel: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      disabled={!!busy}
      className="px-sm py-sm bg-primary-container text-on-primary-container rounded-lg text-xs font-semibold flex items-center justify-center gap-2 disabled:opacity-40"
    >
      <span className="material-symbols-outlined text-sm">{icon}</span>
      {busy === label ? workingLabel : label}
    </button>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-surface-container-low border border-white/10 rounded p-sm">
      <p className="font-label-caps text-[10px] text-outline">{label}</p>
      <p className="font-data-mono text-lg text-on-surface">{value}</p>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const danger = ['missing', 'bad_magic', 'too_small', 'link_broken', 'error', 'pending', 'expired'].includes(status);
  const ready = ['server_ok', 'verified', 'completed', 'staging'].includes(status);
  const color = ready ? 'text-tertiary border-tertiary/30 bg-tertiary/10' : danger ? 'text-error border-error/30 bg-error/10' : 'text-cyan-300 border-cyan-400/30 bg-cyan-400/10';
  return <span className={`inline-flex px-2 py-0.5 rounded border text-[10px] uppercase font-data-mono ${color}`}>{status}</span>;
}

function formatBytes(value?: number | null) {
  if (!value) return '-';
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}
