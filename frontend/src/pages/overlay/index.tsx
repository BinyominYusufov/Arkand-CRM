import { useMemo, useState } from "react";
import { Download } from "lucide-react";
import { useTranslation } from "react-i18next";

import {
  downloadOverlayExport,
  useOverlayCash,
  useOverlayDebts,
  useOverlayPayroll,
  useOverlaySummary,
} from "@/entities/overlay";
import { apiErrorOf } from "@/shared/api";
import { formatMoney } from "@/shared/lib/money";
import {
  BrandLogo,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Loading,
  Money,
} from "@/shared/ui";
import { BusinessBarChart, businessColorMap } from "@/widgets/report-charts";

/** Холдинг / overlay Части 7: консолидация по всем бизнесам (только владельцы). */
export function OverlayPage() {
  const { t } = useTranslation();
  const summary = useOverlaySummary();
  const cash = useOverlayCash();
  const debts = useOverlayDebts();
  const payroll = useOverlayPayroll();

  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const doExport = async () => {
    setExporting(true);
    setExportError(null);
    try {
      await downloadOverlayExport();
    } catch (e) {
      setExportError(apiErrorOf(e).message);
    } finally {
      setExporting(false);
    }
  };

  const colorOf = useMemo(
    () => businessColorMap(summary.data?.businesses.map((b) => b.business_id) ?? []),
    [summary.data],
  );

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <BrandLogo height={30} />
          <div>
            <h1>{t("overlay.title")}</h1>
            <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
              {t("overlay.subtitle")}
            </div>
          </div>
        </div>
        <div className="page-header__actions">
          <span style={{ fontSize: 12, color: "var(--text-faint)" }}>
            {t("overlay.exportHint")}
          </span>
          <Button
            variant="primary"
            icon={Download}
            onClick={doExport}
            disabled={exporting}
          >
            {t("overlay.export")}
          </Button>
        </div>
      </div>

      <ErrorBanner error={exportError} />

      {summary.isPending ? (
        <Loading />
      ) : summary.isError ? (
        <ErrorBanner error={apiErrorOf(summary.error)} />
      ) : (
        <>
          <div className="kpi-grid">
            <Card title={t("overlay.kpiIncome")}>
              <div className="kpi-value">
                <Money value={summary.data.total.income} direction="in" withIcon />
              </div>
            </Card>
            <Card title={t("overlay.kpiExpense")}>
              <div className="kpi-value">
                <Money value={summary.data.total.expense} direction="out" withIcon />
              </div>
            </Card>
            <Card title={t("overlay.kpiProfit")}>
              <div className="kpi-value">
                <Money value={summary.data.total.profit} />
              </div>
            </Card>
            <Card title={t("overlay.kpiDebts")}>
              <div className="kpi-value">
                <Money value={summary.data.open_debts_total} />
              </div>
            </Card>
            <Card title={t("overlay.kpiCash")}>
              <div className="kpi-value">
                <Money value={summary.data.cash_balance_total} />
              </div>
            </Card>
          </div>

          <h2 className="section-title">{t("overlay.businesses")}</h2>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>{t("common.business")}</th>
                  <th className="num">{t("reports.income")}</th>
                  <th className="num">{t("reports.expense")}</th>
                  <th className="num">{t("reports.profit")}</th>
                </tr>
              </thead>
              <tbody>
                {summary.data.businesses.length === 0 && (
                  <tr>
                    <td colSpan={4}>
                      <EmptyState />
                    </td>
                  </tr>
                )}
                {summary.data.businesses.map((r) => (
                  <tr key={r.business_id}>
                    <td>{r.business_name}</td>
                    <td className="num">
                      <Money value={r.income} direction="in" withIcon withSign />
                    </td>
                    <td className="num">
                      <Money value={r.expense} direction="out" withIcon withSign />
                    </td>
                    <td className="num">
                      <Money value={r.profit} />
                    </td>
                  </tr>
                ))}
                <tr style={{ fontWeight: 600 }}>
                  <td>{t("common.total")}</td>
                  <td className="num">
                    <Money value={summary.data.total.income} direction="in" withSign />
                  </td>
                  <td className="num">
                    <Money value={summary.data.total.expense} direction="out" withSign />
                  </td>
                  <td className="num">
                    <Money value={summary.data.total.profit} />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {summary.data.businesses.length > 0 && (
            <>
              <h2 className="section-title">{t("reports.byBusiness")}</h2>
              <Card>
                <BusinessBarChart
                  rows={summary.data.businesses.map((b) => ({
                    id: b.business_id,
                    name: b.business_name,
                    value: Number.parseFloat(b.income),
                  }))}
                  colorOf={colorOf}
                  name={t("reports.income")}
                />
              </Card>
            </>
          )}
        </>
      )}

      <h2 className="section-title">{t("cash.registers")}</h2>
      {cash.isPending ? (
        <Loading />
      ) : cash.isError ? (
        <ErrorBanner error={apiErrorOf(cash.error)} />
      ) : (
        <div className="tbl-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>{t("cash.register")}</th>
                <th>{t("common.business")}</th>
                <th className="num">{t("cash.balance")}</th>
              </tr>
            </thead>
            <tbody>
              {cash.data.registers.length === 0 && (
                <tr>
                  <td colSpan={3}>
                    <EmptyState />
                  </td>
                </tr>
              )}
              {cash.data.registers.map((r) => (
                <tr key={r.id}>
                  <td>{r.name}</td>
                  <td>{r.business_name}</td>
                  <td className="num">
                    <Money value={r.balance} />
                  </td>
                </tr>
              ))}
              <tr style={{ fontWeight: 600 }}>
                <td colSpan={2}>{t("common.total")}</td>
                <td className="num">
                  <Money value={cash.data.total_balance} />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      <h2 className="section-title">{t("settlements.debts")}</h2>
      {debts.isPending ? (
        <Loading />
      ) : debts.isError ? (
        <ErrorBanner error={apiErrorOf(debts.error)} />
      ) : (
        <>
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
                {debts.data.pairs.length === 0 && (
                  <tr>
                    <td colSpan={4}>
                      <EmptyState />
                    </td>
                  </tr>
                )}
                {debts.data.pairs.map((p) => (
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
          <div
            style={{
              fontSize: 13,
              color: "var(--text-muted)",
              margin: "8px 0 0",
            }}
          >
            {t("settlements.openDebtsTotal")}: {formatMoney(debts.data.total_open)}
          </div>
        </>
      )}

      <h2 className="section-title">{t("payroll.fund")}</h2>
      {payroll.isPending ? (
        <Loading />
      ) : payroll.isError ? (
        <ErrorBanner error={apiErrorOf(payroll.error)} />
      ) : (
        <div className="tbl-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>{t("common.business")}</th>
                <th className="num">{t("payroll.base")}</th>
                <th className="num">{t("payroll.bonus")}</th>
                <th className="num">{t("payroll.fund")}</th>
              </tr>
            </thead>
            <tbody>
              {payroll.data.fund_by_business.length === 0 && (
                <tr>
                  <td colSpan={4}>
                    <EmptyState />
                  </td>
                </tr>
              )}
              {payroll.data.fund_by_business.map((r, i) => (
                <tr key={r.business_id ?? `hq-${i}`}>
                  <td>{r.business_name}</td>
                  <td className="num">{formatMoney(r.base)}</td>
                  <td className="num">{formatMoney(r.bonus)}</td>
                  <td className="num">{formatMoney(r.fund)}</td>
                </tr>
              ))}
              <tr style={{ fontWeight: 600 }}>
                <td colSpan={3}>{t("common.total")}</td>
                <td className="num">{formatMoney(payroll.data.fund_total)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
