import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import ru from "./ru.json";
import tj from "./tj.json";

const LANG_KEY = "arkand_lang";

export function initI18n(lng?: string) {
  if (i18n.isInitialized) return i18n;
  i18n.use(initReactI18next).init({
    resources: {
      ru: { translation: ru },
      tj: { translation: tj },
    },
    lng: lng ?? localStorage.getItem(LANG_KEY) ?? "ru",
    fallbackLng: "ru",
    interpolation: { escapeValue: false },
  });
  return i18n;
}

export function switchLanguage(lng: "ru" | "tj") {
  localStorage.setItem(LANG_KEY, lng);
  void i18n.changeLanguage(lng);
}

export { i18n };
