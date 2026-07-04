import { Globe } from "lucide-react";
import { useTranslation } from "react-i18next";

import { switchLanguage } from "@/shared/lib/i18n";

import "./lang-switcher.css";

/** Переключатель ru ↔ tj: глобус + сегмент из двух кнопок (спека §4.5).
 *  Подпись таджикского — «TJ», <html lang> обновляется в switchLanguage. */
export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const current = i18n.language;
  return (
    <div className="lang-switcher" role="group" aria-label="Language">
      <Globe size={15} className="lang-switcher__globe" aria-hidden />
      <div className="lang-switcher__track">
        {(["ru", "tj"] as const).map((lng) => (
          <button
            key={lng}
            type="button"
            className={`lang-switcher__btn${current === lng ? " lang-switcher__btn--active" : ""}`}
            onClick={() => switchLanguage(lng)}
            aria-pressed={current === lng}
          >
            {lng.toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  );
}
