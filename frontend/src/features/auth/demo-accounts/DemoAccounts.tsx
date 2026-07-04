import { ChevronRight, Info } from "lucide-react";
import { useTranslation } from "react-i18next";

import { SHOW_DEMO } from "@/shared/config/env";

import {
  DEMO_PASSWORD,
  EMAIL_DOMAIN,
  featuredAccounts,
  type DemoAccount,
} from "./accounts";
import "./demo-accounts.css";

interface DemoAccountsProps {
  /** Клик по аккаунту только заполняет форму; вход всё равно через API. */
  onPick: (email: string, password: string) => void;
}

function AccountChip({
  account,
  onPick,
}: {
  account: DemoAccount;
  onPick: DemoAccountsProps["onPick"];
}) {
  const { t } = useTranslation();
  const meta = account.unit ?? (account.roleKey ? t(`login.roles.${account.roleKey}`) : "");
  return (
    <button
      type="button"
      className="demo-chip"
      onClick={() => onPick(account.user + EMAIL_DOMAIN, DEMO_PASSWORD)}
    >
      <span className="demo-chip__badge" aria-hidden>
        {account.user[0].toUpperCase()}
      </span>
      <span className="demo-chip__name">{account.user}</span>
      {meta && <span className="demo-chip__meta">{meta}</span>}
    </button>
  );
}

/** Панель «Демо-доступ»: только в dev или при VITE_SHOW_DEMO=true. */
export function DemoAccounts({ onPick }: DemoAccountsProps) {
  const { t } = useTranslation();
  if (!SHOW_DEMO) return null;
  return (
    <section className="demo-panel" aria-label={t("login.demoTitle")}>
      <header className="demo-panel__head">
        <span className="demo-panel__title">
          <Info size={14} aria-hidden />
          {t("login.demoTitle")}
        </span>
        <span className="demo-panel__pw">
          {t("login.demoPw")} <code>{DEMO_PASSWORD}</code>
        </span>
      </header>
      <p className="demo-panel__hint">
        <ChevronRight size={13} aria-hidden />
        {t("login.demoHint")}
      </p>
      {/* По одному представителю на отдел — компактно, в один экран. */}
      {featuredAccounts.map((account) => (
        <div key={account.group} className="demo-panel__group">
          <div className="demo-panel__group-title">
            {t(`login.groups.${account.group}`)}
          </div>
          <div className="demo-panel__chips">
            <AccountChip account={account} onPick={onPick} />
          </div>
        </div>
      ))}
    </section>
  );
}
