import { useLocation, useNavigate } from 'react-router-dom';

export type RunNavState = {
  from?: string;
  fromLabel?: string;
};

export function runNavState(from: string, fromLabel?: string): RunNavState {
  return { from, fromLabel };
}

export function useRunBackNavigation(fallbackPath = '/admin/dashboard', fallbackLabel = '返回') {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state as RunNavState | null) ?? {};

  const goBack = () => {
    if (state.from) {
      navigate(state.from);
      return;
    }
    if (window.history.length > 1) {
      navigate(-1);
      return;
    }
    navigate(fallbackPath);
  };

  return {
    goBack,
    backLabel: state.fromLabel || fallbackLabel,
  };
}
