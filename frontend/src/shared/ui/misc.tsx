import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { ApiError } from "@/shared/api";

export function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`card ${className}`.trim()}>
      {title && <div className="card__title">{title}</div>}
      {children}
    </div>
  );
}

export function PageHeader({
  title,
  actions,
}: {
  title: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-header">
      <h1>{title}</h1>
      {actions && <div className="page-header__actions">{actions}</div>}
    </div>
  );
}

export function Loading() {
  const { t } = useTranslation();
  return <div className="empty-state">{t("common.loading")}</div>;
}

export function EmptyState({ text }: { text?: string }) {
  const { t } = useTranslation();
  return <div className="empty-state">{text ?? t("common.empty")}</div>;
}

export function ErrorBanner({ error }: { error: ApiError | string | null }) {
  if (!error) return null;
  const message = typeof error === "string" ? error : error.message;
  return (
    <div className="error-banner" role="alert">
      {message}
    </div>
  );
}

export function ProgressBar({
  percent,
  tone = "var(--success)",
}: {
  percent: number;
  tone?: string;
}) {
  const width = Math.min(Math.max(percent, 0), 100);
  return (
    <div className="progress">
      <div className="progress__bar" style={{ width: `${width}%`, background: tone }} />
    </div>
  );
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: { key: string; label: string }[];
  active: string;
  onChange: (key: string) => void;
}) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          role="tab"
          aria-selected={active === tab.key}
          className={`tabs__tab${active === tab.key ? " tabs__tab--active" : ""}`}
          onClick={() => onChange(tab.key)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
