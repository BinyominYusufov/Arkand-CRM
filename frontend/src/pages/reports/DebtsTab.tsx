import { useTranslation } from "react-i18next";

import { useDebtsReport } from "@/entities/report";
import { apiErrorOf } from "@/shared/api";
import { formatMoney } from "@/shared/lib/money";
import { Card, EmptyState, ErrorBanner, Loading, StatusBadge } from "@/shared/ui";

/** ФНС-12 · Взаиморасчёты: кто кому должен + реестр долгов. */
export function DebtsTab() {
  const { t } = useTranslation();
  const report = useDebtsReport();

  if (report.isPending) return <Loading />;
  if (report.isError) return <ErrorBanner error={apiErrorOf(report.error)} />;

  const { debts, pairs, total_open } = report.data;

  return (
    <div>
      <div className="kpi-grid">
        <Card title={t("settlements.openDebtsTotal")}>
          <div className="kpi-value">{formatMoney(total_open)}</div>
        </Card>
      </div>

      <h3 className="section-title">{t("settlements.whoOwes")}</h3>
      <div className="tbl-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th>{t("settlements.debtor")}</th>
              <th>{t("settlements.creditor")}</th>
              <th className="num">{t("settlements.remaining")}</th>
              <th className="num">{t("settlements.debts")}</th>
            </tr>
          </thead>
          <tbody>
            {pairs.length === 0 && (
              <tr>
                <td colSpan={4}>
                  <EmptyState />
                </td>
              </tr>
            )}
            {pairs.map((p) => (
              <tr key={`${p.debtor_name}-${p.creditor_name}`}>
                <td>{p.debtor_name}</td>
                <td>{p.creditor_name}</td>
                <td className="num">{formatMoney(p.total_remaining)}</td>
                <td className="num">{p.debts_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="section-title">{t("settlements.registry")}</h3>
      <div className="tbl-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th>{t("settlements.debtor")}</th>
              <th>{t("settlements.creditor")}</th>
              <th className="num">{t("common.amount")}</th>
              <th className="num">{t("settlements.remaining")}</th>
              <th>{t("common.date")}</th>
              <th>{t("common.status")}</th>
            </tr>
          </thead>
          <tbody>
            {debts.length === 0 && (
              <tr>
                <td colSpan={6}>
                  <EmptyState />
                </td>
              </tr>
            )}
            {debts.map((d) => (
              <tr key={d.id}>
                <td>{d.debtor_name}</td>
                <td>{d.creditor_name}</td>
                <td className="num">{formatMoney(d.amount)}</td>
                <td className="num">{formatMoney(d.remaining)}</td>
                <td>{new Date(d.created_at).toLocaleDateString("ru-RU")}</td>
                <td>
                  <StatusBadge status={d.is_overdue ? "overdue" : "open"} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
