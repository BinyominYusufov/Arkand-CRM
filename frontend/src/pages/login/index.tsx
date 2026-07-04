import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Trans, useTranslation } from "react-i18next";

import { homeRoute, useMe } from "@/entities/session";
import { LoginForm, type LoginPrefill } from "@/features/auth/LoginForm";
import { DemoAccounts } from "@/features/auth/demo-accounts/DemoAccounts";
import { LanguageSwitcher } from "@/features/language-switcher";
import { tokenStorage } from "@/shared/api";
import { PhoenixMark } from "@/shared/ui";

import "./login.css";

const UNITS = ["Строй-Инвест", "Проект-Бюро", "Завод Алмосӣ", "Завод Сомон"];

export function LoginPage() {
  const { t } = useTranslation();
  const [prefill, setPrefill] = useState<LoginPrefill | undefined>();
  // Залогиненный пользователь на /login — сразу в приложение.
  const { data: me } = useMe(Boolean(tokenStorage.access));
  if (me) return <Navigate to={homeRoute(me)} replace />;

  return (
    <div className="login-layout">
      <aside className="login-brand">
        <div className="login-brand__top">
          <PhoenixMark className="login-brand__phoenix" />
          <div className="login-brand__wordmark">ARKAND</div>
          <div className="login-brand__rule" aria-hidden />
          <div className="login-brand__kicker">{t("login.brandKicker")}</div>
        </div>
        <p className="login-brand__lede">
          <Trans i18nKey="login.brandLede" components={{ b: <b /> }} />
        </p>
        <div className="login-brand__units">
          <div className="login-brand__units-label">{t("login.unitsLabel")}</div>
          <div className="login-brand__chips">
            {UNITS.map((unit) => (
              <span key={unit} className="login-brand__chip">
                {unit}
              </span>
            ))}
          </div>
        </div>
      </aside>

      <main className="login-side">
        <div className="login-side__lang">
          <LanguageSwitcher />
        </div>
        <div className="login-side__inner">
          <h1 className="login-side__title">{t("login.title")}</h1>
          <p className="login-side__subtitle">{t("login.subtitle")}</p>
          <LoginForm prefill={prefill} />
          <DemoAccounts
            onPick={(email, password) =>
              setPrefill({ email, password, nonce: Date.now() })
            }
          />
        </div>
      </main>
    </div>
  );
}
