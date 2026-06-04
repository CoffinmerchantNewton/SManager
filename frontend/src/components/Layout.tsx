import { useEffect, useState, type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';

interface LayoutProps {
  children: ReactNode;
}

type ThemeMode = 'research' | 'pig';

const THEME_STORAGE_KEY = 'smanager-theme';

const navItems = [
  { path: '/admin/dashboard', match: 'dashboard', label: 'Dashboard', sideLabel: 'Dashboard', icon: 'dashboard' },
  { path: '/admin/runs', match: 'runs', label: 'Runs', sideLabel: 'Run Control', icon: 'rocket_launch' },
  { path: '/admin/fnl', match: 'fnl', label: 'FNL', sideLabel: 'FNL Manager', icon: 'cloud_sync' },
  { path: '/admin/workflow', match: 'workflow', label: 'Workflow', sideLabel: 'Workflow DAG', icon: 'account_tree' },
  { path: '/admin/scheduler', match: 'scheduler', label: 'Scheduler', sideLabel: 'Task Scheduler', icon: 'schedule' },
  { path: '/admin/products', match: 'products', label: 'Products', sideLabel: 'Forecast Models', icon: 'analytics' },
];

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const [theme, setTheme] = useState<ThemeMode>(() => {
    if (typeof window === 'undefined') {
      return 'research';
    }
    return window.localStorage.getItem(THEME_STORAGE_KEY) === 'pig' ? 'pig' : 'research';
  });

  const isActive = (path: string) => location.pathname.includes(path);
  const switchTheme = (nextTheme: ThemeMode) => {
    setTheme(nextTheme);
    window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
  };

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  return (
    <div data-theme={theme} className="min-h-screen bg-background text-on-background transition-colors duration-300">
      {/* TopNavBar */}
      <header className="fixed top-0 w-full h-14 flex justify-between items-center px-6 z-50 bg-surface-container-lowest/95 backdrop-blur-md border-b border-outline-variant font-inter tracking-tight antialiased text-sm">
        <div className="flex items-center gap-8">
          <span className="text-lg font-black tracking-tighter text-on-surface uppercase">
            China Pollen Forecast System
          </span>
          <nav className="hidden md:flex gap-6">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`${
                  isActive(item.match)
                    ? 'text-secondary-container border-b-2 border-secondary-container pb-1'
                    : 'text-on-surface-variant hover:text-secondary hover:bg-white/5 transition-colors'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex h-9 items-center rounded-lg border border-outline-variant bg-surface-container-high p-1">
            {(['research', 'pig'] as ThemeMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => switchTheme(mode)}
                aria-pressed={theme === mode}
                className={`min-w-[56px] rounded px-2.5 py-1 text-[11px] font-label-caps transition-colors ${
                  theme === mode
                    ? 'bg-primary-container text-on-primary-container'
                    : 'text-on-surface-variant hover:text-on-surface'
                }`}
              >
                {mode === 'research' ? '科研' : '小猪'}
              </button>
            ))}
          </div>
          <button className="p-2 text-on-surface-variant hover:text-on-surface transition-colors">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <button className="p-2 text-on-surface-variant hover:text-on-surface transition-colors">
            <span className="material-symbols-outlined">account_circle</span>
          </button>
        </div>
      </header>

      {/* SideNavBar */}
      <aside className="fixed left-0 top-14 h-[calc(100vh-3.5rem)] flex flex-col py-4 z-40 bg-surface-container-lowest w-64 border-r border-outline-variant font-inter text-xs uppercase tracking-widest font-semibold">
        <div className="px-6 mb-8">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-primary-container/20 flex items-center justify-center border border-primary-container/30">
              <span className="material-symbols-outlined text-primary scale-75">terminal</span>
            </div>
            <div>
              <p className="text-on-surface font-bold tracking-normal text-sm">Telemetry Admin</p>
              <p className="text-outline lowercase tracking-normal text-[10px]">Node: Beijing-01</p>
            </div>
          </div>
        </div>
        <nav className="flex-1 px-3 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-4 px-3 py-2.5 rounded-lg transition-all duration-200 ${
                isActive(item.match)
                  ? 'bg-primary-container/10 text-secondary-container border-r-2 border-secondary-container'
                  : 'text-outline hover:text-on-surface-variant hover:bg-white/5'
              }`}
            >
              <span className="material-symbols-outlined scale-90">{item.icon}</span>
              <span>{item.sideLabel}</span>
            </Link>
          ))}
        </nav>
        <div className="px-4 mt-auto">
          <button className="w-full py-3 bg-surface-container-high border border-outline-variant text-on-surface rounded-lg hover:bg-surface-variant transition-colors flex items-center justify-center gap-2">
            <span className="material-symbols-outlined text-[18px]">add_box</span>
            New Simulation
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="ml-64 mt-14 min-h-[calc(100vh-3.5rem)]">{children}</main>
    </div>
  );
}
