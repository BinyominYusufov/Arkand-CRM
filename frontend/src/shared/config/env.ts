/** Чтение VITE_*-переменных окружения — единственная точка доступа к env. */

/** База API. По умолчанию — прокси-путь Vite (/api/v1 → 127.0.0.1:8000). */
export const API_URL: string = import.meta.env.VITE_API_URL ?? "/api/v1";

/** Панель «Демо-доступ»: видна в dev или при VITE_SHOW_DEMO=true. */
export const SHOW_DEMO: boolean =
  import.meta.env.DEV || import.meta.env.VITE_SHOW_DEMO === "true";
