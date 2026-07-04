import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

import { API_URL } from "@/shared/config/env";

const ACCESS_KEY = "arkand_access";
const REFRESH_KEY = "arkand_refresh";

export const tokenStorage = {
  get access(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const token = tokenStorage.access;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string> | null = null;

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined;
    if (
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      tokenStorage.refresh &&
      !original.url?.includes("/auth/")
    ) {
      original._retry = true;
      try {
        refreshing ??= axios
          .post(`${API_URL}/auth/refresh`, { refresh: tokenStorage.refresh })
          .then((res) => {
            tokenStorage.set(res.data.access);
            return res.data.access as string;
          })
          .finally(() => {
            refreshing = null;
          });
        const access = await refreshing;
        original.headers.Authorization = `Bearer ${access}`;
        return api(original);
      } catch {
        tokenStorage.clear();
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  },
);

/** Единый формат ошибки API: { code, message, details } */
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export function apiErrorOf(e: unknown): ApiError {
  if (axios.isAxiosError(e) && e.response?.data && typeof e.response.data === "object") {
    const d = e.response.data as Partial<ApiError>;
    if (d.code && d.message) {
      return { code: d.code, message: d.message, details: d.details };
    }
  }
  return { code: "network_error", message: e instanceof Error ? e.message : "Ошибка сети" };
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
