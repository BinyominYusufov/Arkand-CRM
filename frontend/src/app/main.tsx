import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";

// Брендовые шрифты (страница входа): Golos Text — UI, Cormorant Garamond —
// вордмарк/лид, Noto Sans — фолбэк таджикских глифов (ӣ ҳ ӯ қ ғ ҷ).
import "@fontsource/golos-text/400.css";
import "@fontsource/golos-text/500.css";
import "@fontsource/golos-text/600.css";
import "@fontsource/cormorant-garamond/600.css";
import "@fontsource/noto-sans/400.css";
import "@fontsource/noto-sans/500.css";

import "@/shared/config/global.css";
import "@/shared/ui";
import { initI18n } from "@/shared/lib/i18n";
import { queryClient } from "@/shared/api";

import { App } from "./App";

initI18n();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
