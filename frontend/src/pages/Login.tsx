import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { authApi, setAuthToken } from '../services/api';
import { errorMessage } from '../utils/errors';

interface LoginProps {
  onLogin: (token: string) => void;
}

export default function Login({ onLogin }: LoginProps) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const redirectTo = params.get('from') || (location.state as { from?: string } | null)?.from || '/admin/dashboard';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const response = await authApi.login(username, password);
      const token = response.data.access_token;
      setAuthToken(token);
      onLogin(token);
      navigate(redirectTo, { replace: true });
    } catch (err: unknown) {
      setError(errorMessage(err, 'Invalid username or password'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/80 backdrop-blur-sm">
      <div className="w-full max-w-[400px] bg-surface-container border border-white/10 glow-border p-xl flex flex-col relative">
        {/* Decorative Tech Corner Elements */}
        <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-secondary-container"></div>
        <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-secondary-container"></div>
        <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-secondary-container"></div>
        <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-secondary-container"></div>

        {/* Header Section */}
        <div className="mb-xl flex items-center gap-md">
          <div className="w-10 h-10 bg-primary-container/10 border border-primary-container/30 flex items-center justify-center">
            <span className="material-symbols-outlined text-primary-container" style={{ fontVariationSettings: "'wght' 700" }}>
              lock
            </span>
          </div>
          <div>
            <h2 className="font-headline-md text-headline-md text-on-surface">管理员登录</h2>
            <p className="font-label-caps text-label-caps text-outline uppercase tracking-widest mt-1">
              SYSTEM AUTHENTICATION REQUIRED
            </p>
          </div>
        </div>

        {/* Input Form */}
        <form className="flex flex-col gap-lg" onSubmit={handleSubmit}>
          <div className="space-y-sm">
            <label className="font-label-caps text-label-caps text-on-surface-variant flex justify-between items-center">
              <span>请输入控制台账号</span>
              <span className="text-[10px] text-primary">ENCRYPTED PORTAL</span>
            </label>
            <input
              autoFocus
              className="mb-3 w-full bg-surface-container-low border border-outline-variant px-md py-sm font-data-mono text-data-mono text-white focus:outline-none focus:border-secondary-container focus:ring-1 focus:ring-secondary-container/30 transition-all placeholder:text-outline-variant"
              placeholder="admin"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <div className="relative">
              <input
                className="w-full bg-surface-container-low border border-outline-variant px-md py-sm font-data-mono text-data-mono text-white focus:outline-none focus:border-secondary-container focus:ring-1 focus:ring-secondary-container/30 transition-all placeholder:text-outline-variant"
                placeholder="••••••••"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <span className="absolute right-md top-1/2 -translate-y-1/2 material-symbols-outlined text-outline-variant cursor-pointer hover:text-on-surface transition-colors">
                visibility
              </span>
            </div>
            {error && <p className="text-error text-xs">{error}</p>}
          </div>
          <div className="flex flex-col gap-md pt-md">
            <button
              type="submit"
              disabled={busy}
              className="w-full bg-primary-container py-md text-white font-label-caps text-label-caps tracking-[0.2em] hover:brightness-110 active:scale-[0.98] transition-all flex items-center justify-center gap-md disabled:opacity-50"
            >
              {busy ? 'AUTHENTICATING' : 'AUTHENTICATE'}
              <span className="material-symbols-outlined text-sm">login</span>
            </button>
            <div className="flex items-center justify-between">
              <a
                className="text-[11px] font-label-caps text-outline hover:text-on-surface transition-colors flex items-center gap-xs"
                href="#"
              >
                <span className="material-symbols-outlined text-xs">help_outline</span>
                FORGOT ACCESS KEY?
              </a>
              <span className="text-[10px] font-data-mono text-outline/30 uppercase">v4.2.0-STABLE</span>
            </div>
          </div>
        </form>

        {/* Bottom Data Stream Decoration */}
        <div className="mt-xl h-1 w-full bg-white/5 overflow-hidden">
          <div className="h-full w-1/3 bg-secondary-container animate-[slide_2s_infinite_linear]"></div>
        </div>
        <style>{`
          @keyframes slide {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(300%); }
          }
        `}</style>
      </div>
    </div>
  );
}
