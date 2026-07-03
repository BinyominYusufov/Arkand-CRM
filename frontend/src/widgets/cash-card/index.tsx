import { AlertTriangle } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { CashRegister } from "@/entities/cash-register";
import { formatMoney } from "@/shared/lib/money";
import { Money, ProgressBar } from "@/shared/ui";

/** Цвет заполнения лимита: <70% — success, 70–100% — warning, >100% — error. */
export function utilizationTone(percent: number): string {
  if (percent > 100) return "var(--error)";
  if (percent >= 70) return "var(--warning)";
  return "var(--success)";
}

/** Карточка кассы: имя + бизнес, остаток, лимит/оборот месяца, прогресс лимита. */
export function CashCard({ register }: { register: CashRegister }) {
  const { t } = useTranslation();
  const utilization = register.limit_utilization;
  const tone = utilizationTone(utilization);

  return (
    <div className="card" data-testid={`cash-card-${register.id}`}>
      <div className="card__title">
        {register.name} · {register.business_name}
      </div>
      <div className="kpi-value">
        <Money value={register.balance} />
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 8,
          fontSize: 12,
          color: "var(--text-muted)",
          margin: "8px 0 2px",
        }}
      >
        <span>{t("cash.limit")}</span>
        <span style={{ fontVariantNumeric: "tabular-nums" }}>
          {formatMoney(register.turnover_limit)}
        </span>
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 8,
          fontSize: 12,
          color: "var(--text-muted)",
          marginBottom: 8,
        }}
      >
        <span>{t("cash.turnover")}</span>
        <span style={{ fontVariantNumeric: "tabular-nums" }}>
          {formatMoney(register.month_turnover)}
        </span>
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 8,
          fontSize: 12,
          color: "var(--text-muted)",
          marginBottom: 4,
        }}
      >
        <span>{t("cash.utilization")}</span>
        <span style={{ fontVariantNumeric: "tabular-nums" }}>
          {Math.round(utilization)}%
        </span>
      </div>
      <ProgressBar percent={utilization} tone={tone} />
      {register.over_limit && (
        <span className="badge badge--error" style={{ marginTop: 8 }}>
          <AlertTriangle size={13} aria-hidden />
          {t("cash.overLimit")}
        </span>
      )}
    </div>
  );
}
