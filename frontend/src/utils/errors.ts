interface ApiErrorShape {
  response?: {
    data?: {
      detail?: string | { message?: string };
    };
  };
  message?: string;
}

export function errorMessage(error: unknown, fallback: string): string {
  const candidate = error as ApiErrorShape;
  const detail = candidate?.response?.data?.detail;
  if (typeof detail === 'string') {
    return detail;
  }
  if (detail && typeof detail.message === 'string') {
    return detail.message;
  }
  if (typeof candidate?.message === 'string') {
    return candidate.message;
  }
  return fallback;
}
