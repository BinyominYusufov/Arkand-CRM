import { useTranslation } from "react-i18next";

import { LoginForm } from "@/features/auth/LoginForm";
import { LanguageSwitcher } from "@/features/language-switcher";
import { BrandLogo, Card } from "@/shared/ui";

export function LoginPage() {
  const { t } = useTranslation();
  return (
    <div
      style={{
        minHeight: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--paper)",
        padding: 16,
      }}
    >
      <div style={{ width: 360 }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 20 }}>
          <BrandLogo variant="full" height={36} />
        </div>
        <Card>
          <h1 style={{ fontSize: 17, marginBottom: 2 }}>{t("auth.title")}</h1>
          <p style={{ margin: "0 0 14px", color: "var(--text-muted)", fontSize: 13 }}>
            {t("auth.subtitle")}
          </p>
          <LoginForm />
          <p
            style={{
              margin: "14px 0 0",
              fontSize: 12,
              lineHeight: 1.5,
              color: "var(--text-muted)",
            }}
          >
            {t("auth.demoHint")}
          </p>
        </Card>
        <div style={{ display: "flex", justifyContent: "center", marginTop: 12 }}>
          <LanguageSwitcher />
        </div>
      </div>
    </div>
  );
}
