import { Navigate, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { homeRoute, useMe } from "@/entities/session";
import { LoginPage } from "@/pages/login";
import { FinancePage } from "@/pages/finance";
import { CashPage } from "@/pages/cash";
import { SettlementsPage } from "@/pages/settlements";
import { PayrollPage } from "@/pages/payroll";
import { ReportsPage } from "@/pages/reports";
import { OverlayPage } from "@/pages/overlay";

import { AppLayout } from "./AppLayout";
import { RequireAuth, RequirePerm } from "./ProtectedRoute";

function HomeRedirect() {
  const { data: me } = useMe();
  if (!me) return null;
  return <Navigate to={homeRoute(me)} replace />;
}

function NotFound() {
  const { t } = useTranslation();
  return <div className="empty-state">{t("common.notFound")}</div>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route index element={<HomeRedirect />} />
          <Route
            path="/finance"
            element={
              <RequirePerm perm="finance.view">
                <FinancePage />
              </RequirePerm>
            }
          />
          <Route
            path="/cash"
            element={
              <RequirePerm perm="cash.view">
                <CashPage />
              </RequirePerm>
            }
          />
          <Route
            path="/settlements"
            element={
              <RequirePerm perm="settlements.view">
                <SettlementsPage />
              </RequirePerm>
            }
          />
          <Route
            path="/payroll"
            element={
              <RequirePerm perm="payroll.view">
                <PayrollPage />
              </RequirePerm>
            }
          />
          <Route
            path="/reports"
            element={
              <RequirePerm perm="reports.view">
                <ReportsPage />
              </RequirePerm>
            }
          />
          <Route
            path="/overlay"
            element={
              <RequirePerm perm="overlay.view">
                <OverlayPage />
              </RequirePerm>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  );
}
