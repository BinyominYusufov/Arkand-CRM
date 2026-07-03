import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { useBusinesses } from "@/entities/business";
import { usePayrollReport } from "@/entities/report";
import { apiErrorOf } from "@/shared/api";
import { formatMoney } from "@/shared/lib/money";
import {
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  Loading,
  Money,
  Select,
  StatusBadge,
} from "@/shared/ui";
import { BusinessBarChart, businessColorMap } from "@/widgets/report-charts";

const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1);

/** ФНС-13 · Зарплатный фонд и прибыль. */
export function PayrollTab() {
  const { t } = useTranslation();
  const [year, setYear] = useState("");
  const [month, setMonth] = useState("");

  const report = usePayrollReport({
    year: year ? Number(year) : undefined,
    month: month ? Number(month) : undefined,
  });
  const businesses = useBusinesses();

  const colorOf = useMemo(
    () =>
      businessColorMap(
        businesses.data?.map((b) => b.id) ??
          report.data?.fund_by_business.map((r) => r.business_id) ??
          [],
      ),
    [businesses.data, report.data],
  );

  const currentYear = new Date().getFullYear();
  const years = [currentYear - 2, currentYear - 1, currentYear];

  return (
    <div>
      <div className="filters-bar">
        <Field label={t("payroll.year")}>
          <Select value={year} onChange={(e) => setYear(e.target.value)}>
            <option value="">—</option>
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("payroll.month")}>
          <Select value={month} onChange={(e) => setMonth(e.target.value)}>
            <option value="">—</option>
            {MONTHS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      {report.isPending ? (
        <Loading />
      ) : report.isError ? (
        <ErrorBanner error={apiErrorOf(report.error)} />
      ) : (
        <>
          {report.data.period && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 12,
                fontSize: 13,
                color: "var(--text-muted)",
              }}
            >
              <span>
                {t("common.period")}:{" "}
                {String(report.data.period.month).padStart(2, "0")}.
                {report.data.period.year}
              </span>
              <StatusBadge status={report.data.period.status} />
            </div>
          )}

          <h3 className="section-title">{t("payroll.fund")}</h3>
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
                {report.data.fund_by_business.length === 0 && (
                  <tr>
                    <td colSpan={4}>
                      <EmptyState />
                    </td>
                  </tr>
                )}
                {report.data.fund_by_business.map((r, i) => (
                  <tr key={r.business_id ?? `hq-${i}`}>
                    <td>{r.business_name}</td>
                    <td className="num">{formatMoney(r.base)}</td>
                    <td className="num">{formatMoney(r.bonus)}</td>
                    <td className="num">{formatMoney(r.fund)}</td>
                  </tr>
                ))}
                <tr style={{ fontWeight: 600 }}>
                  <td colSpan={3}>{t("common.total")}</td>
                  <td className="num">{formatMoney(report.data.fund_total)}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {report.data.fund_by_business.length > 0 && (
            <Card>
              <BusinessBarChart
                rows={report.data.fund_by_business.map((r) => ({
                  id: r.business_id,
                  name: r.business_name,
                  value: Number.parseFloat(r.fund),
                }))}
                colorOf={colorOf}
                name={t("payroll.fund")}
              />
            </Card>
          )}

          <h3 className="section-title">{t("finance.profitByBusiness")}</h3>
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
                {report.data.profit_by_business.length === 0 && (
                  <tr>
                    <td colSpan={4}>
                      <EmptyState />
                    </td>
                  </tr>
                )}
                {report.data.profit_by_business.map((r) => (
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
                  <td>{t("reports.holdingTotal")}</td>
                  <td className="num">
                    <Money value={report.data.profit_total.income} direction="in" withSign />
                  </td>
                  <td className="num">
                    <Money
                      value={report.data.profit_total.expense}
                      direction="out"
                      withSign
                    />
                  </td>
                  <td className="num">
                    <Money value={report.data.profit_total.profit} />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
