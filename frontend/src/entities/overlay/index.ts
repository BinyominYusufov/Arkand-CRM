import { useQuery } from "@tanstack/react-query";

import { api } from "@/shared/api";
import type { CashflowRow, CashRegistersReport, DebtsReport, PayrollReport } from "@/entities/report";

export interface OverlaySummary {
  businesses: CashflowRow[];
  total: { income: string; expense: string; profit: string };
  open_debts_total: string;
  cash_balance_total: string;
  businesses_count: number;
}

export function useOverlaySummary() {
  return useQuery({
    queryKey: ["overlay-summary"],
    queryFn: async () => (await api.get<OverlaySummary>("/overlay/summary")).data,
  });
}

export function useOverlayCash() {
  return useQuery({
    queryKey: ["overlay-cash"],
    queryFn: async () => (await api.get<CashRegistersReport>("/overlay/cash")).data,
  });
}

export function useOverlayDebts() {
  return useQuery({
    queryKey: ["overlay-debts"],
    queryFn: async () => (await api.get<DebtsReport>("/overlay/debts")).data,
  });
}

export function useOverlayPayroll() {
  return useQuery({
    queryKey: ["overlay-payroll"],
    queryFn: async () => (await api.get<PayrollReport>("/overlay/payroll")).data,
  });
}

/** Экспорт консолидации: скачивает версионируемый JSON (контракт Части 7). */
export async function downloadOverlayExport() {
  const { data } = await api.get("/overlay/export");
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `arkand-overlay-v${data.version}.json`;
  a.click();
  URL.revokeObjectURL(url);
}
