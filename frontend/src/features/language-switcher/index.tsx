import { useTranslation } from "react-i18next";

import { switchLanguage } from "@/shared/lib/i18n";

/** Переключатель ru ↔ tj. */
export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const current = i18n.language;
  return (
    <div style={{ display: "inline-flex", gap: 2 }} role="group" aria-label="Language">
      {(["ru", "tj"] as const).map((lng) => (
        <button
          key={lng}
          type="button"
          className={`tabs__tab${current === lng ? " tabs__tab--active" : ""}`}
          style={{ padding: "3px 8px", fontSize: 12 }}
          onClick={() => switchLanguage(lng)}
          aria-pressed={current === lng}
        >
          {lng.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
