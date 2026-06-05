import { type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useThemeMode, type ThemeMode } from '../hooks/useThemeMode';
import { LanguageSelector, useI18n } from '../i18n';

interface LayoutProps {
  children: ReactNode;
}

const navItems = [
  { path: '/admin/dashboard', match: 'dashboard', labelKey: 'navDashboard', icon: 'dashboard' },
  { path: '/admin/runs', match: 'runs', labelKey: 'navRuns', icon: 'rocket_launch' },
  { path: '/admin/fnl', match: 'fnl', labelKey: 'navFnl', icon: 'cloud_sync' },
  { path: '/admin/workflow', match: 'workflow', labelKey: 'navWorkflow', icon: 'account_tree' },
  { path: '/admin/scheduler', match: 'scheduler', labelKey: 'navScheduler', icon: 'schedule' },
  { path: '/admin/products', match: 'products', labelKey: 'navProducts', icon: 'analytics' },
];

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const { theme, switchTheme } = useThemeMode();
  const { t } = useI18n();

  const isActive = (path: string) => location.pathname.includes(path);

  return (
    <div data-theme={theme} className="min-h-screen bg-background text-on-background transition-colors duration-300">
      <aside className="fixed left-0 top-0 z-40 flex h-screen w-64 flex-col border-r border-outline-variant bg-surface-container-lowest py-4 font-inter text-xs font-semibold uppercase tracking-widest">
        <div className="mb-8 px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-primary-container/30 bg-primary-container/20">
              <span className="material-symbols-outlined scale-75 text-primary">terminal</span>
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-bold tracking-normal text-on-surface">{t('telemetryAdmin')}</p>
              <p className="truncate text-[10px] normal-case tracking-normal text-outline">{t('nodeLabel')}</p>
            </div>
          </div>
          <p className="mt-4 text-[10px] font-black leading-tight tracking-wide text-on-surface">{t('appName')}</p>
        </div>

        <nav className="flex-1 space-y-1 px-3">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-4 rounded-lg px-3 py-2.5 transition-all duration-200 ${
                isActive(item.match)
                  ? 'border-r-2 border-secondary-container bg-primary-container/10 text-secondary-container'
                  : 'text-outline hover:bg-white/5 hover:text-on-surface-variant'
              }`}
            >
              <span className="material-symbols-outlined scale-90">{item.icon}</span>
              <span>{t(item.labelKey)}</span>
            </Link>
          ))}
        </nav>

        <div className="mt-auto space-y-3 px-4">
          <LanguageSelector compact />
          <div>
            <span className="mb-1 block font-label-caps text-[10px] uppercase text-outline">{t('theme')}</span>
            <div className="flex h-9 items-center rounded-lg border border-outline-variant bg-surface-container-high p-1">
              {(['research', 'pig'] as ThemeMode[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => switchTheme(mode)}
                  aria-pressed={theme === mode}
                  className={`min-w-0 flex-1 rounded px-2 py-1 text-[11px] font-label-caps transition-colors ${
                    theme === mode
                      ? 'bg-primary-container text-on-primary-container'
                      : 'text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  {mode === 'research' ? t('themeResearch') : t('themePig')}
                </button>
              ))}
            </div>
          </div>
          <button className="flex w-full items-center justify-center gap-2 rounded-lg border border-outline-variant bg-surface-container-high py-3 text-on-surface transition-colors hover:bg-surface-variant">
            <span className="material-symbols-outlined text-[18px]">add_box</span>
            {t('newSimulation')}
          </button>
        </div>
      </aside>

      <main className="ml-64 min-h-screen">{children}</main>
    </div>
  );
}
