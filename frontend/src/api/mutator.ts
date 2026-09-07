type ApiError = Error & {
  status?: number;
  body?: unknown;
};

const ACCESS_TOKEN_KEY = 'accessToken';
const REFRESH_TOKEN_KEY = 'refreshToken';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';
export const AUTH_EXPIRED_EVENT = 'auth-expired';

function getAccessToken() {
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

function getRefreshToken() {
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

function saveAccessToken(accessToken: string) {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
}

function clearTokens() {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

function notifyAuthExpired() {
  window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
}

async function refreshAccessToken() {
  const refresh = getRefreshToken();

  if (!refresh) {
    notifyAuthExpired();
    return null;
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/auth/token/refresh/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh }),
  });

  if (!response.ok) {
    clearTokens();
    notifyAuthExpired();
    return null;
  }

  const data = await response.json();
  saveAccessToken(data.access);

  return data.access;
}

async function sendRequest(
  url: string,
  options: RequestInit,
  token: string | null,
) {
  const isFormData = options.body instanceof FormData;

  return fetch(url, {
    ...options,
    headers: {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
}

export async function apiFetch<T>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  let response = await sendRequest(url, options, getAccessToken());

  if (response.status === 401) {
    const newAccessToken = await refreshAccessToken();

    if (newAccessToken) {
      response = await sendRequest(url, options, newAccessToken);
    }
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const error: ApiError = new Error(
      errorBody?.error?.message ?? 'Request failed',
    );
    error.status = response.status;
    error.body = errorBody;
    throw error;
  }

  if (response.status === 204) {
    return {
      data: null,
      status: response.status,
      headers: response.headers,
    } as T;
  }

  const contentType = response.headers.get('content-type') ?? '';
  const data = contentType.includes('application/json')
    ? await response.json()
    : await response.blob();

  return {
    data,
    status: response.status,
    headers: response.headers,
  } as T;
}
