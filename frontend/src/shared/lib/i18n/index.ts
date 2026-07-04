import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import ru from "./ru.json";
import tj from "./tj.json";

const LANG_KEY = "arkand_lang";

/** Внутренний код таджикской локали в проекте — "tj"; в <html lang> — ISO "tg". */
function htmlLangOf(lng: string): string {
  return lng === "tj" ? "tg" : lng;
}

export function initI18n(lng?: string) {
  if (i18n.isInitialized) return i18n;
  const initial = lng ?? localStorage.getItem(LANG_KEY) ?? "ru";
  i18n.use(initReactI18next).init({
    resources: {
      ru: { translation: ru },
      tj: { translation: tj },
    },
    lng: initial,
    fallbackLng: "ru",
    interpolation: { escapeValue: false },
  });
  document.documentElement.lang = htmlLangOf(initial);
  return i18n;
}

export function switchLanguage(lng: "ru" | "tj") {
  localStorage.setItem(LANG_KEY, lng);
  document.documentElement.lang = htmlLangOf(lng);
  void i18n.changeLanguage(lng);
}

export { i18n };
