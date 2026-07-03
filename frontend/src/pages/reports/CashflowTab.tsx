import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { useBusinesses } from "@/entities/business";
import {
  useCashflowMonthly,
  useCashflowReport,
  useExpensesByCategory,
} from "@/entities/report";
import { apiErrorOf } from "@/shared/api";
import { Card, EmptyState, ErrorBanner, Field, Input, Loading, Money } from "@/shared/ui";
import {
  businessColorMap,
  ExpenseCategoryBarChart,
  IncomeExpenseBarChart,
  MonthlyIncomeLineChart,
} from "@/widgets/report-charts";

/** ФНС-10 · Поступления и расходы по бизнесам. */
export function CashflowTab() {
  const { t } = useTranslation();
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const params = {
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  };

  const cashflow = useCashflowReport(params);
  const monthly = useCashflowMonthly();
  const categories = useExpensesByCategory(params);
  const businesses = useBusinesses();

  /* Цвета серий — по полному списку бизнесов, чтобы фильтры их не меняли. */
  const colorOf = useMemo(
    () =>
      businessColorMap(
        businesses.data?.map((b) => b.id) ??
          cashflow.data?.businesses.map((b) => b.business_id) ??
          [],
      ),
    [businesses.data, cashflow.data],
  );

  return (
    <div>
      <div className="filters-bar">
        <Field label={t("common.from")}>
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </Field>
        <Field label={t("common.to")}>
          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </Field>
      </div>

      {cashflow.isPending ? (
        <Loading />
      ) : cashflow.isError ? (
        <ErrorBanner error={apiErrorOf(cashflow.error)} />
      ) : (
        <>
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
                {cashflow.data.businesses.length === 0 && (
                  <tr>
                    <td colSpan={4}>
                      <EmptyState />
                    </td>
                  </tr>
                )}
                {cashflow.data.businesses.map((r) => (
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
                    <Money value={cashflow.data.total.income} direction="in" withSign />
                  </td>
                  <td className="num">
                    <Money value={cashflow.data.total.expense} direction="out" withSign />
                  </td>
                  <td className="num">
                    <Money value={cashflow.data.total.profit} />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <h3 className="section-title">{t("reports.monthly")}</h3>
          <Card>
            {monthly.isPending ? (
              <Loading />
            ) : monthly.isError ? (
              <ErrorBanner error={apiErrorOf(monthly.error)} />
            ) : monthly.data.rows.length === 0 ? (
              <EmptyState />
            ) : (
              <MonthlyIncomeLineChart rows={monthly.data.rows} colorOf={colorOf} />
            )}
          </Card>

          <h3 className="section-title">{t("reports.byBusiness")}</h3>
          <Card>
            {cashflow.data.businesses.length === 0 ? (
              <EmptyState />
            ) : (
              <IncomeExpenseBarChart rows={cashflow.data.businesses} />
            )}
          </Card>

          <h3 className="section-title">{t("reports.byCategory")}</h3>
          <Card>
            {categories.isPending ? (
              <Loading />
            ) : categories.isError ? (
              <ErrorBanner error={apiErrorOf(categories.error)} />
            ) : categories.data.rows.length === 0 ? (
              <EmptyState />
            ) : (
              <ExpenseCategoryBarChart rows={categories.data.rows} />
            )}
          </Card>
        </>
      )}
    </div>
  );
}
