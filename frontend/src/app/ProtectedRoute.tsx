import { Navigate, Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { hasPerm, useMe } from "@/entities/session";
import { tokenStorage } from "@/shared/api";
import { Loading } from "@/shared/ui";

/** Доступ только аутентифицированным; при отсутствии токена — на /login. */
export function RequireAuth() {
  const { data: me, isLoading, isError } = useMe();
  if (!tokenStorage.access) return <Navigate to="/login" replace />;
  if (isLoading) return <Loading />;
  if (isError || !me) return <Navigate to="/login" replace />;
  return <Outlet context={me} />;
}

/** Доступ к разделу по коду права из data-driven RBAC. */
export function RequirePerm({ perm, children }: { perm: string; children: React.ReactNode }) {
  const { t } = useTranslation();
  const { data: me, isLoading } = useMe();
  if (isLoading) return <Loading />;
  if (!hasPerm(me, perm)) {
    return <div className="empty-state">{t("common.forbidden")}</div>;
  }
  return <>{children}</>;
}
