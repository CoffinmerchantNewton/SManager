import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useI18n } from '../i18n';
import { serverApi } from '../services/api';
import type { ServerConfig, ServerDaemonStatus, ServerRegionInfo } from '../types';
import { errorMessage } from '../utils/errors';

/** 服务器 registry 未返回时的展示名（内部名 → 中文） */
const REGION_FALLBACK: Record<string, { display_name: string; slurm_code: string }> = {
  Beijing: { display_name: '北京', slurm_code: 'BJ' },
  InnerMG: { display_name: '内蒙古', slurm_code: 'IMG' },
  Shaanxi: { display_name: '陕西', slurm_code: 'SX' },
  Yulin: { display_name: '榆林', slurm_code: 'YL' },
  China: { display_name: '全国', slurm_code: 'CN' },
};

function mergeRegionList(apiList: ServerRegionInfo[], configRegions?: string[]): ServerRegionInfo[] {
  const map = new Map<string, ServerRegionInfo>();
  for (const item of apiList) {
    map.set(item.region, item);
  }
  for (const key of configRegions ?? []) {
    if (!map.has(key)) {
      const fb = REGION_FALLBACK[key];
      map.set(key, {
        region: key,
        display_name: fb?.display_name ?? key,
        seasons: [],
        slurm_code: fb?.slurm_code ?? '',
      });
    }
  }
  return [...map.values()].sort((a, b) => a.region.localeCompare(b.region));
}

export default function RunOperations() {
  const { t } = useI18n();
  const [status, setStatus] = useState<ServerDaemonStatus | null>(null);
  const [config, setConfig] = useState<ServerConfig | null>(null);
  const [regions, setRegions] = useState<ServerRegionInfo[]>([]);
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [stale, setStale] = useState(false);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setMessage('');
    try {
      const [statusRes, configRes, regionsRes] = await Promise.all([
        serverApi.status(),
        serverApi.config(),
        serverApi.regions(),
      ]);
      const st = statusRes.data?.data?.payload as ServerDaemonStatus | undefined;
      const cfg = configRes.data?.data?.config as ServerConfig | undefined;
      const regList = (regionsRes.data?.data?.regions || []) as ServerRegionInfo[];

      setStatus(st || null);
      setConfig(cfg || null);
      setRegions(mergeRegionList(regList, cfg?.forecast?.regions));
      setStale(Boolean(statusRes.data?.data?.stale || configRes.data?.data?.stale));
      if (cfg?.forecast?.regions?.length) {
        setSelectedRegions(cfg.forecast.regions);
      } else {
        setSelectedRegions(regList.map((r) => r.region));
      }
    } catch (err: unknown) {
      setMessage(errorMessage(err, '加载服务器状态失败'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const runAction = async (label: string, action: () => Promise<void>) => {
    setBusy(label);
    setMessage('');
    try {
      await action();
    } catch (err: unknown) {
      setMessage(errorMessage(err, '操作失败'));
    } finally {
      setBusy('');
    }
  };

  const handleScheduleToggle = (enabled: boolean) =>
    runAction('schedule', async () => {
      if (enabled) {
        await serverApi.enableSchedule();
        setMessage('定时调度已启用');
      } else {
        await serverApi.disableSchedule();
        setMessage('定时调度已停用');
      }
      await loadAll();
    });

  const handleSaveRegions = () =>
    runAction('regions', async () => {
      if (selectedRegions.length === 0) {
        setMessage('请至少选择一个区域');
        return;
      }
      await serverApi.updateConfig({ regions: selectedRegions });
      setMessage('预报区域配置已保存');
      await loadAll();
    });

  const handleSubmitForecast = (force: boolean) =>
    runAction(force ? 'force' : 'submit', async () => {
      const res = await serverApi.submitForecast({
        force,
        regions: selectedRegions.length ? selectedRegions : undefined,
      });
      const data = res.data?.data;
      const tick = data?.tick as { regions_submitted?: string[]; regions_skipped?: string[] } | undefined;
      const submitted = tick?.regions_submitted?.length ?? 0;
      const skipped = tick?.regions_skipped?.length ?? 0;
      setMessage(
        data?.message ||
          `${force ? '强制提交' : '提交预报'}完成：提交 ${submitted} 个区域，跳过 ${skipped} 个`,
      );
      await loadAll();
    });

  const handleReconcile = () =>
    runAction('reconcile', async () => {
      await serverApi.reconcile();
      setMessage('Reconcile 已触发（含 squeue/sacct 异常检测）');
      await loadAll();
    });

  const toggleRegion = (region: string) => {
    setSelectedRegions((current) =>
      current.includes(region) ? current.filter((item) => item !== region) : [...current, region],
    );
  };

  const scheduleEnabled = config?.schedule?.enabled ?? status?.schedule_enabled ?? false;
  const tickTime = config?.schedule?.tick_time || '07:30';

  return (
    <div className="min-h-full p-lg technical-grid flex flex-col gap-gutter">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-headline-xl text-headline-xl text-on-surface">{t('navRuns')}</h1>
          <p className="font-body-md text-outline">
            管理 smanager-server 定时调度与预报区域；季节由服务器按月份自动选择（3–6 春 / 7–10 秋）
          </p>
          {stale && <p className="mt-2 text-xs text-amber-300">服务器暂不可达，展示缓存数据。</p>}
        </div>
        <button
          onClick={() => void loadAll()}
          disabled={loading || !!busy}
          className="rounded-lg border border-white/10 bg-surface-container-high px-md py-sm text-sm text-on-surface hover:bg-white/10 disabled:opacity-40"
        >
          <span className="material-symbols-outlined mr-2 align-middle text-sm">refresh</span>
          {t('refresh')}
        </button>
      </header>

      {message && (
        <div className="rounded-lg border border-white/10 bg-surface-container-low p-md text-sm text-on-surface">
          {message}
        </div>
      )}

      <Panel title="定时任务开关" loading={loading && !config}>
        <div className="flex flex-col gap-md sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-on-surface">
              每日自动预报 Tick
              <span className={`ml-2 rounded px-2 py-0.5 text-[10px] font-semibold ${scheduleEnabled ? 'bg-primary-container text-on-primary-container' : 'bg-surface-container-high text-outline'}`}>
                {scheduleEnabled ? '已启用' : '已关闭'}
              </span>
            </p>
            <p className="mt-1 text-xs text-outline">
              北京时间每天 {tickTime} 自动扫描 FNL、创建 repair request 并提交各区域 Slurm 任务
            </p>
            {status?.next_tick_at && (
              <p className="mt-1 text-xs text-cyan-300/80">下次执行：{formatTime(status.next_tick_at)}</p>
            )}
          </div>
          <Toggle
            checked={scheduleEnabled}
            disabled={!!busy}
            onChange={(checked) => void handleScheduleToggle(checked)}
          />
        </div>
      </Panel>

      <section className="grid grid-cols-1 gap-gutter xl:grid-cols-1">
        <Panel title="服务器状态" loading={loading && !status}>
          {status ? (
            <div className="space-y-sm text-sm">
              <div className="flex flex-wrap gap-2">
                <StatusPill active={scheduleEnabled} label={scheduleEnabled ? '调度运行中' : '调度已停止'} />
                <StatusPill active={(status.active_runs ?? 0) > 0} label={`活跃 Run ${status.active_runs ?? 0}`} />
              </div>
              <SummaryRow label="服务器时间" value={formatTime(status.server_time_local)} />
              <SummaryRow label="上次 Tick" value={status.last_tick_result || '-'} />
              <SummaryRow label="下次 Tick" value={status.next_tick_at || '-'} />
              <SummaryRow label="待补 FNL" value={`${status.pending_repairs ?? 0}`} danger={(status.pending_repairs ?? 0) > 0} />
            </div>
          ) : (
            <p className="text-sm text-amber-300">无法连接 smanager-server，请检查 backend/.env 中的 SERVER_API_BASE_URL</p>
          )}
        </Panel>
      </section>

      <Panel title={`预报区域 (${selectedRegions.length}/${regions.length})`}>
        <div className="mb-md grid grid-cols-1 gap-sm md:grid-cols-2 xl:grid-cols-3">
          {regions.map((r) => (
            <label
              key={r.region}
              className="flex cursor-pointer items-center gap-2 rounded border border-white/10 bg-surface-container-low px-sm py-sm text-sm"
            >
              <input
                type="checkbox"
                checked={selectedRegions.includes(r.region)}
                onChange={() => toggleRegion(r.region)}
              />
              <span>
                {r.display_name || r.region}
                <span className="ml-1 text-xs text-outline">({r.slurm_code})</span>
              </span>
            </label>
          ))}
          {regions.length === 0 && !loading && (
            <p className="text-sm text-outline">当前月份无可用区域，或服务器不可达。</p>
          )}
        </div>
        <div className="flex flex-wrap gap-sm">
          <button
            type="button"
            className="rounded border border-white/10 px-sm py-xs text-xs text-on-surface hover:bg-white/5"
            onClick={() => setSelectedRegions(regions.map((r) => r.region))}
          >
            全选
          </button>
          <button
            type="button"
            className="rounded border border-white/10 px-sm py-xs text-xs text-on-surface hover:bg-white/5"
            onClick={() => setSelectedRegions([])}
          >
            清空
          </button>
          <button
            type="button"
            disabled={!!busy}
            className="rounded bg-primary-container px-md py-xs text-xs font-semibold text-on-primary-container disabled:opacity-40"
            onClick={() => void handleSaveRegions()}
          >
            保存区域配置
          </button>
        </div>
      </Panel>

      <Panel title="手动操作">
        <div className="flex flex-wrap gap-sm">
          <ActionButton
            icon="play_circle"
            label="提交预报 (Tick)"
            primary
            disabled={!!busy}
            onClick={() => void handleSubmitForecast(false)}
          />
          <ActionButton
            icon="bolt"
            label="强制提交 (force)"
            disabled={!!busy}
            onClick={() => void handleSubmitForecast(true)}
          />
          <ActionButton
            icon="sync"
            label="Reconcile"
            disabled={!!busy}
            onClick={() => void handleReconcile()}
          />
        </div>
        <p className="mt-md text-xs text-outline">
          「提交预报」按当前月份自动季节与区域扫描缺失 FNL 并创建 Run；「强制提交」忽略部分重复检查。
        </p>
        <Link to="/admin" className="mt-sm inline-flex items-center gap-1 text-xs text-cyan-300 hover:text-cyan-200">
          返回 Dashboard 查看 Run 列表
          <span className="material-symbols-outlined text-sm">arrow_forward</span>
        </Link>
      </Panel>
    </div>
  );
}

function Panel({ title, children, loading }: { title: string; children: ReactNode; loading?: boolean }) {
  return (
    <div className="rounded-lg border border-white/10 bg-surface-container p-md">
      <h2 className="mb-md font-label-caps text-label-caps uppercase text-outline">{title}</h2>
      {loading ? <p className="text-sm text-outline">加载中…</p> : children}
    </div>
  );
}

function SummaryRow({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-outline">{label}</span>
      <span className={`font-data-mono text-xs ${danger ? 'text-error' : 'text-on-surface'}`}>{value}</span>
    </div>
  );
}

function StatusPill({ active, label }: { active: boolean; label: string }) {
  return (
    <span
      className={`rounded-full px-sm py-0.5 text-[10px] font-semibold uppercase ${
        active ? 'bg-primary-container text-on-primary-container' : 'bg-surface-container-high text-outline'
      }`}
    >
      {label}
    </span>
  );
}

function Toggle({
  checked,
  disabled,
  onChange,
}: {
  checked: boolean;
  disabled?: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative h-7 w-12 rounded-full transition-colors disabled:opacity-40 ${
        checked ? 'bg-primary' : 'bg-surface-container-high'
      }`}
    >
      <span
        className={`absolute top-0.5 h-6 w-6 rounded-full bg-on-primary transition-transform ${
          checked ? 'left-[22px]' : 'left-0.5'
        }`}
      />
    </button>
  );
}

function ActionButton({
  icon,
  label,
  primary,
  disabled,
  onClick,
}: {
  icon: string;
  label: string;
  primary?: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-lg px-md py-sm text-sm disabled:opacity-40 ${
        primary
          ? 'bg-primary text-on-primary hover:opacity-90'
          : 'border border-white/10 bg-surface-container-high text-on-surface hover:bg-white/10'
      }`}
    >
      <span className="material-symbols-outlined text-base">{icon}</span>
      {label}
    </button>
  );
}

function formatTime(value?: string | null) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
}
