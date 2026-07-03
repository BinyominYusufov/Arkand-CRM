import { useQuery } from "@tanstack/react-query";

import { api } from "@/shared/api";

export interface CashflowRow {
  business_id: number;
  business_name: string;
  income: string;
  expense: string;
  profit: string;
}

export interface CashflowReport {
  businesses: CashflowRow[];
  total: { income: string; expense: string; profit: string };
}

export interface MonthlyRow {
  month: string;
  business_id: number;
  business_name: string;
  income: string;
  expense: string;
}

export interface CashRegisterRow {
  id: number;
  name: string;
  business_id: number;
  business_name: string;
  balance: string;
  month_turnover: string;
  turnover_limit: string;
  limit_utilization: number;
  over_limit: boolean;
}

export interface CashRegistersReport {
  registers: CashRegisterRow[];
  total_balance: string;
  total_month_turnover: string;
}

export interface DebtsReport {
  debts: {
    id: number;
    debtor_name: string;
    creditor_name: string;
    amount: string;
    remaining: string;
    is_overdue: boolean;
    created_at: string;
  }[];
  pairs: {
    debtor_name: string;
    creditor_name: string;
    total_remaining: string;
    debts_count: number;
  }[];
  total_open: string;
}

export interface PayrollReport {
  period: { year: number; month: number; status: string } | null;
  fund_by_business: {
    business_id: number | null;
    business_name: string;
    base: string;
    bonus: string;
    fund: string;
  }[];
  fund_total: string;
  profit_by_business: CashflowRow[];
  profit_total: { income: string; expense: string; profit: string };
  runs: { id: number; year: number; month: number; status: string; fund: string }[];
}

export interface ExpenseCategoryRow {
  category_id: number | null;
  category_name: string;
  total: string;
  count: number;
}

const clean = (params: Record<string, unknown>) =>
  Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== "" && v !== undefined && v !== null),
  );

export function useCashflowReport(params: { date_from?: string; date_to?: string } = {}) {
  return useQuery({
    queryKey: ["report-cashflow", params],
    queryFn: async () =>
      (await api.get<CashflowReport>("/reports/cashflow", { params: clean(params) })).data,
  });
}

export function useCashflowMonthly(months = 6) {
  return useQuery({
    queryKey: ["report-cashflow-monthly", months],
    queryFn: async () =>
      (
        await api.get<{ months: number; rows: MonthlyRow[] }>("/reports/cashflow/monthly", {
          params: { months },
        })
      ).data,
  });
}

export function useExpensesByCategory(params: { date_from?: string; date_to?: string } = {}) {
  return useQuery({
    queryKey: ["report-expense-category", params],
    queryFn: async () =>
      (
        await api.get<{ rows: ExpenseCategoryRow[] }>("/reports/expenses/by-category", {
          params: clean(params),
        })
      ).data,
  });
}

export function useCashRegistersReport() {
  return useQuery({
    queryKey: ["report-cash-registers"],
    queryFn: async () =>
      (await api.get<CashRegistersReport>("/reports/cash-registers")).data,
  });
}

export function useDebtsReport() {
  return useQuery({
    queryKey: ["report-debts"],
    queryFn: async () => (await api.get<DebtsReport>("/reports/debts")).data,
  });
}

export function usePayrollReport(params: { year?: number; month?: number } = {}) {
  return useQuery({
    queryKey: ["report-payroll", params],
    queryFn: async () =>
      (await api.get<PayrollReport>("/reports/payroll", { params: clean(params) })).data,
  });
}
