import { useEffect, useState } from 'react';

export type ThemeMode = 'research' | 'pig';

const THEME_STORAGE_KEY = 'smanager-theme';

export function useThemeMode() {
  const [theme, setTheme] = useState<ThemeMode>(() => {
    if (typeof window === 'undefined') {
      return 'research';
    }
    return window.localStorage.getItem(THEME_STORAGE_KEY) === 'pig' ? 'pig' : 'research';
  });

  const switchTheme = (nextTheme: ThemeMode) => {
    setTheme(nextTheme);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    }
  };

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  return { theme, switchTheme };
}
