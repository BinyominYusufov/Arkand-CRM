import { useState } from "react";
import { useTranslation } from "react-i18next";

import { BarterSection } from "@/features/barter";
import { TransfersSection } from "@/features/transfer-actions";
import { PageHeader, Tabs } from "@/shared/ui";
import { DebtRegistry } from "@/widgets/debt-registry";

/** Взаиморасчёты: реестр долгов, передачи между бизнесами, бартер. */
export function SettlementsPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState("registry");

  return (
    <>
      <PageHeader title={t("settlements.title")} />
      <Tabs
        tabs={[
          { key: "registry", label: t("settlements.registry") },
          { key: "transfers", label: t("settlements.transfers") },
          { key: "barters", label: t("settlements.barters") },
        ]}
        active={tab}
        onChange={setTab}
      />
      {tab === "registry" && <DebtRegistry />}
      {tab === "transfers" && <TransfersSection />}
      {tab === "barters" && <BarterSection />}
    </>
  );
}
