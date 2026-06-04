import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();

  const isActive = (path: string) => location.pathname.includes(path);

  return (
    <div className="min-h-screen bg-background text-on-background">
      {/* TopNavBar */}
      <header className="fixed top-0 w-full h-14 flex justify-between items-center px-6 z-50 bg-slate-950/95 backdrop-blur-md border-b border-white/10 font-inter tracking-tight antialiased text-sm">
        <div className="flex items-center gap-8">
          <span className="text-lg font-black tracking-tighter text-white uppercase">
            China Pollen Forecast System
          </span>
          <nav className="hidden md:flex gap-6">
            <Link
              to="/admin/dashboard"
              className={`${
                isActive('dashboard')
                  ? 'text-cyan-400 border-b-2 border-cyan-400 pb-1'
                  : 'text-slate-400 hover:text-cyan-300 hover:bg-white/5 transition-colors'
              }`}
            >
              Dashboard
            </Link>
            <Link
              to="/admin/runs"
              className={`${
                isActive('runs')
                  ? 'text-cyan-400 border-b-2 border-cyan-400 pb-1'
                  : 'text-slate-400 hover:text-cyan-300 hover:bg-white/5 transition-colors'
              }`}
            >
              Runs
            </Link>
            <Link
              to="/admin/fnl"
              className={`${
                isActive('fnl')
                  ? 'text-cyan-400 border-b-2 border-cyan-400 pb-1'
                  : 'text-slate-400 hover:text-cyan-300 hover:bg-white/5 transition-colors'
              }`}
            >
              FNL
            </Link>
            <Link
              to="/admin/workflow"
              className={`${
                isActive('workflow')
                  ? 'text-cyan-400 border-b-2 border-cyan-400 pb-1'
                  : 'text-slate-400 hover:text-cyan-300 hover:bg-white/5 transition-colors'
              }`}
            >
              Workflow
            </Link>
            <Link
              to="/admin/scheduler"
              className={`${
                isActive('scheduler')
                  ? 'text-cyan-400 border-b-2 border-cyan-400 pb-1'
                  : 'text-slate-400 hover:text-cyan-300 hover:bg-white/5 transition-colors'
              }`}
            >
              Scheduler
            </Link>
            <Link
              to="/admin/products"
              className={`${
                isActive('products')
                  ? 'text-cyan-400 border-b-2 border-cyan-400 pb-1'
                  : 'text-slate-400 hover:text-cyan-300 hover:bg-white/5 transition-colors'
              }`}
            >
              Products
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <button className="p-2 text-slate-400 hover:text-white transition-colors">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <button className="p-2 text-slate-400 hover:text-white transition-colors">
            <span className="material-symbols-outlined">account_circle</span>
          </button>
        </div>
      </header>

      {/* SideNavBar */}
      <aside className="fixed left-0 top-14 h-[calc(100vh-3.5rem)] flex flex-col py-4 z-40 bg-slate-950 w-64 border-r border-white/10 font-inter text-xs uppercase tracking-widest font-semibold">
        <div className="px-6 mb-8">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-600/20 flex items-center justify-center border border-blue-500/30">
              <span className="material-symbols-outlined text-blue-400 scale-75">terminal</span>
            </div>
            <div>
              <p className="text-white font-bold tracking-normal text-sm">Telemetry Admin</p>
              <p className="text-slate-500 lowercase tracking-normal text-[10px]">Node: Beijing-01</p>
            </div>
          </div>
        </div>
        <nav className="flex-1 px-3 space-y-1">
          <Link
            to="/admin/dashboard"
            className={`flex items-center gap-4 px-3 py-2.5 rounded-lg transition-all duration-200 ${
              isActive('dashboard')
                ? 'bg-blue-600/10 text-cyan-400 border-r-2 border-cyan-400'
                : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
            }`}
          >
            <span className="material-symbols-outlined scale-90">dashboard</span>
            <span>Dashboard</span>
          </Link>
          <Link
            to="/admin/runs"
            className={`flex items-center gap-4 px-3 py-2.5 rounded-lg transition-all duration-200 ${
              isActive('runs')
                ? 'bg-blue-600/10 text-cyan-400 border-r-2 border-cyan-400'
                : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
            }`}
          >
            <span className="material-symbols-outlined scale-90">rocket_launch</span>
            <span>Run Control</span>
          </Link>
          <Link
            to="/admin/fnl"
            className={`flex items-center gap-4 px-3 py-2.5 rounded-lg transition-all duration-200 ${
              isActive('fnl')
                ? 'bg-blue-600/10 text-cyan-400 border-r-2 border-cyan-400'
                : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
            }`}
          >
            <span className="material-symbols-outlined scale-90">cloud_sync</span>
            <span>FNL Manager</span>
          </Link>
          <Link
            to="/admin/workflow"
            className={`flex items-center gap-4 px-3 py-2.5 rounded-lg transition-all duration-200 ${
              isActive('workflow')
                ? 'bg-blue-600/10 text-cyan-400 border-r-2 border-cyan-400'
                : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
            }`}
          >
            <span className="material-symbols-outlined scale-90">account_tree</span>
            <span>Workflow DAG</span>
          </Link>
          <Link
            to="/admin/scheduler"
            className={`flex items-center gap-4 px-3 py-2.5 rounded-lg transition-all duration-200 ${
              isActive('scheduler')
                ? 'bg-blue-600/10 text-cyan-400 border-r-2 border-cyan-400'
                : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
            }`}
          >
            <span className="material-symbols-outlined scale-90">schedule</span>
            <span>Task Scheduler</span>
          </Link>
          <Link
            to="/admin/products"
            className={`flex items-center gap-4 px-3 py-2.5 rounded-lg transition-all duration-200 ${
              isActive('products')
                ? 'bg-blue-600/10 text-cyan-400 border-r-2 border-cyan-400'
                : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
            }`}
          >
            <span className="material-symbols-outlined scale-90">analytics</span>
            <span>Forecast Models</span>
          </Link>
        </nav>
        <div className="px-4 mt-auto">
          <button className="w-full py-3 bg-white/5 border border-white/10 text-white rounded-lg hover:bg-white/10 transition-colors flex items-center justify-center gap-2">
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
