import { useTranslation } from "react-i18next";

import { useProfit } from "@/entities/transaction";
import { AddTransactionControls } from "@/features/add-transaction";
import { TxTable } from "@/widgets/tx-table";
import { apiErrorOf } from "@/shared/api";
import { Card, ErrorBanner, Loading, Money, PageHeader } from "@/shared/ui";

/** Карточки прибыли по бизнесам и итого (ФНС-04). */
function ProfitCards() {
  const { t } = useTranslation();
  const profit = useProfit();

  if (profit.isLoading) return <Loading />;
  if (profit.isError) return <ErrorBanner error={apiErrorOf(profit.error)} />;
  if (!profit.data) return null;

  const cards = [
    ...profit.data.businesses.map((b) => ({
      key: `b-${b.business_id}`,
      title: b.business_name,
      income: b.income,
      expense: b.expense,
      profit: b.profit,
    })),
    {
      key: "total",
      title: t("common.total"),
      income: profit.data.total.income,
      expense: profit.data.total.expense,
      profit: profit.data.total.profit,
    },
  ];

  return (
    <div className="kpi-grid">
      {cards.map((c) => (
        <Card key={c.key} title={c.title}>
          <div className="kpi-value">
            <Money value={c.profit} />
          </div>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 2,
              marginTop: 6,
              fontSize: 12,
              color: "var(--text-muted)",
            }}
          >
            <span>
              {t("finance.income")}: <Money value={c.income} direction="in" />
            </span>
            <span>
              {t("finance.expense")}: <Money value={c.expense} direction="out" />
            </span>
          </div>
        </Card>
      ))}
    </div>
  );
}

export function FinancePage() {
  const { t } = useTranslation();
  return (
    <>
      <PageHeader title={t("finance.title")} actions={<AddTransactionControls />} />
      <h2 className="section-title">{t("finance.profitByBusiness")}</h2>
      <ProfitCards />
      <h2 className="section-title">{t("finance.transactions")}</h2>
      <TxTable />
    </>
  );
}
