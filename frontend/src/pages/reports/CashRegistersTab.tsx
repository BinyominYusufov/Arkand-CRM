import { AlertTriangle } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useCashRegistersReport } from "@/entities/report";
import { apiErrorOf } from "@/shared/api";
import { formatMoney } from "@/shared/lib/money";
import { EmptyState, ErrorBanner, Loading, Money, ProgressBar } from "@/shared/ui";

/** ФНС-11 · Кассы: остатки, обороты, лимиты и их утилизация. */
export function CashRegistersTab() {
  const { t } = useTranslation();
  const report = useCashRegistersReport();

  if (report.isPending) return <Loading />;
  if (report.isError) return <ErrorBanner error={apiErrorOf(report.error)} />;

  const { registers, total_balance, total_month_turnover } = report.data;

  return (
    <div className="tbl-wrap">
      <table className="tbl">
        <thead>
          <tr>
            <th>{t("cash.register")}</th>
            <th>{t("common.business")}</th>
            <th className="num">{t("cash.balance")}</th>
            <th className="num">{t("cash.turnover")}</th>
            <th className="num">{t("cash.limit")}</th>
            <th>{t("cash.utilization")}</th>
          </tr>
        </thead>
        <tbody>
          {registers.length === 0 && (
            <tr>
              <td colSpan={6}>
                <EmptyState />
              </td>
            </tr>
          )}
          {registers.map((r) => {
            const tone = r.over_limit
              ? "var(--error)"
              : r.limit_utilization >= 80
                ? "var(--warning)"
                : "var(--success)";
            return (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>{r.business_name}</td>
                <td className="num">
                  <Money value={r.balance} />
                </td>
                <td className="num">{formatMoney(r.month_turnover)}</td>
                <td className="num">{formatMoney(r.turnover_limit)}</td>
                <td>
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 200 }}
                  >
                    <span
                      style={{
                        width: 44,
                        textAlign: "right",
                        fontVariantNumeric: "tabular-nums",
                      }}
                    >
                      {Math.round(r.limit_utilization)}%
                    </span>
                    <div style={{ flex: 1 }}>
                      <ProgressBar percent={r.limit_utilization} tone={tone} />
                    </div>
                    {r.over_limit && (
                      <span className="badge badge--error">
                        <AlertTriangle size={13} aria-hidden />
                        {t("cash.overLimit")}
                      </span>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
          <tr style={{ fontWeight: 600 }}>
            <td colSpan={2}>{t("common.total")}</td>
            <td className="num">
              <Money value={total_balance} />
            </td>
            <td className="num">{formatMoney(total_month_turnover)}</td>
            <td colSpan={2} />
          </tr>
        </tbody>
      </table>
    </div>
  );
}
