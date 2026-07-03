import { useState } from "react";
import { Printer } from "lucide-react";
import { useTranslation } from "react-i18next";

import { BrandLogo, Button, PageHeader, Tabs } from "@/shared/ui";

import { CashflowTab } from "./CashflowTab";
import { CashRegistersTab } from "./CashRegistersTab";
import { DebtsTab } from "./DebtsTab";
import { PayrollTab } from "./PayrollTab";
import "./reports.css";

type TabKey = "cashflow" | "cash" | "debts" | "payroll";

/** Отчёты ФНС-10…ФНС-13 с печатной шапкой. */
export function ReportsPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<TabKey>("cashflow");

  const fullTitle: Record<TabKey, string> = {
    cashflow: t("reports.cashflowFull"),
    cash: t("reports.cashRegistersFull"),
    debts: t("reports.debtsFull"),
    payroll: t("reports.payrollFull"),
  };

  return (
    <div className="reports-page">
      <div className="report-print-header">
        <BrandLogo height={24} />
        <div>
          <div className="report-print-header__title">{fullTitle[tab]}</div>
          <div className="report-print-header__date">
            {new Date().toLocaleDateString("ru-RU")}
          </div>
        </div>
      </div>

      <PageHeader
        title={t("reports.title")}
        actions={
          <Button icon={Printer} onClick={() => window.print()}>
            {t("reports.print")}
          </Button>
        }
      />

      <Tabs
        tabs={[
          { key: "cashflow", label: t("reports.cashflow") },
          { key: "cash", label: t("reports.cashRegisters") },
          { key: "debts", label: t("reports.debts") },
          { key: "payroll", label: t("reports.payroll") },
        ]}
        active={tab}
        onChange={(k) => setTab(k as TabKey)}
      />

      <h2 className="section-title" style={{ marginTop: 0 }}>
        {fullTitle[tab]}
      </h2>

      {tab === "cashflow" && <CashflowTab />}
      {tab === "cash" && <CashRegistersTab />}
      {tab === "debts" && <DebtsTab />}
      {tab === "payroll" && <PayrollTab />}
    </div>
  );
}
