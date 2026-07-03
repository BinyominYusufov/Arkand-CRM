import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";

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
