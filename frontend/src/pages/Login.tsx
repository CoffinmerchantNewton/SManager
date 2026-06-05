import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { LanguageSelector, useI18n } from '../i18n';
import { authApi, setAuthToken } from '../services/api';
import { errorMessage } from '../utils/errors';

interface LoginProps {
  onLogin: (token: string) => void;
}

export default function Login({ onLogin }: LoginProps) {
  const { t } = useI18n();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
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
      setError(errorMessage(err, t('loginError')));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
      <div className="absolute right-4 top-4 w-44">
        <LanguageSelector compact />
      </div>
      <div className="relative flex w-full max-w-[400px] flex-col border border-white/10 bg-surface-container p-xl glow-border">
        <div className="absolute left-0 top-0 h-2 w-2 border-l border-t border-secondary-container" />
        <div className="absolute right-0 top-0 h-2 w-2 border-r border-t border-secondary-container" />
        <div className="absolute bottom-0 left-0 h-2 w-2 border-b border-l border-secondary-container" />
        <div className="absolute bottom-0 right-0 h-2 w-2 border-b border-r border-secondary-container" />

        <div className="mb-xl flex items-center gap-md">
          <div className="flex h-10 w-10 items-center justify-center border border-primary-container/30 bg-primary-container/10">
            <span className="material-symbols-outlined text-primary-container" style={{ fontVariationSettings: "'wght' 700" }}>
              lock
            </span>
          </div>
          <div>
            <h2 className="font-headline-md text-headline-md text-on-surface">{t('loginTitle')}</h2>
            <p className="mt-1 font-label-caps text-label-caps uppercase tracking-widest text-outline">
              {t('loginSubtitle')}
            </p>
          </div>
        </div>

        <form className="flex flex-col gap-lg" onSubmit={handleSubmit}>
          <div className="space-y-sm">
            <label className="flex items-center justify-between font-label-caps text-label-caps text-on-surface-variant">
              <span>{t('loginAccountLabel')}</span>
              <span className="text-[10px] text-primary">{t('loginAccountHint')}</span>
            </label>
            <input
              autoFocus
              className="mb-3 w-full border border-outline-variant bg-surface-container-low px-md py-sm font-data-mono text-data-mono text-white transition-all placeholder:text-outline-variant focus:border-secondary-container focus:outline-none focus:ring-1 focus:ring-secondary-container/30"
              placeholder={t('loginUsernamePlaceholder')}
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <div className="relative">
              <input
                className="w-full border border-outline-variant bg-surface-container-low px-md py-sm pr-10 font-data-mono text-data-mono text-white transition-all placeholder:text-outline-variant focus:border-secondary-container focus:outline-none focus:ring-1 focus:ring-secondary-container/30"
                placeholder={t('loginPasswordPlaceholder')}
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowPassword((current) => !current)}
                className="material-symbols-outlined absolute right-md top-1/2 -translate-y-1/2 text-outline-variant transition-colors hover:text-on-surface"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? 'visibility_off' : 'visibility'}
              </button>
            </div>
            {error && <p className="text-xs text-error">{error}</p>}
          </div>
          <div className="flex flex-col gap-md pt-md">
            <button
              type="submit"
              disabled={busy}
              className="flex w-full items-center justify-center gap-md bg-primary-container py-md font-label-caps text-label-caps tracking-[0.2em] text-white transition-all hover:brightness-110 active:scale-[0.98] disabled:opacity-50"
            >
              {busy ? t('loginBusy') : t('loginSubmit')}
              <span className="material-symbols-outlined text-sm">login</span>
            </button>
            <div className="flex items-center justify-between">
              <a
                className="flex items-center gap-xs text-[11px] font-label-caps text-outline transition-colors hover:text-on-surface"
                href="#"
              >
                <span className="material-symbols-outlined text-xs">help_outline</span>
                {t('loginForgot')}
              </a>
              <span className="font-data-mono text-[10px] uppercase text-outline/30">v4.2.0-STABLE</span>
            </div>
          </div>
        </form>

        <div className="mt-xl h-1 w-full overflow-hidden bg-white/5">
          <div className="h-full w-1/3 bg-secondary-container animate-[slide_2s_infinite_linear]" />
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
