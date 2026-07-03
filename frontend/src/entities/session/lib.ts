import type { Me } from "./types";

/** Проверка права из data-driven RBAC (список приходит в /me). */
export function hasPerm(me: Me | undefined, perm: string): boolean {
  return Boolean(me?.permissions.includes(perm));
}

/** Стартовый раздел по роли: кассир — кассы, владелец — холдинг, остальные — финансы. */
export function homeRoute(me: Me | undefined): string {
  if (!me) return "/login";
  if (hasPerm(me, "finance.view")) return "/finance";
  if (hasPerm(me, "overlay.view")) return "/overlay";
  if (hasPerm(me, "cash.view")) return "/cash";
  if (hasPerm(me, "reports.view")) return "/reports";
  return "/cash";
}
