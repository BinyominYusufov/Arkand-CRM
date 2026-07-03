import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type Paginated } from "@/shared/api";

export interface ExpenseCategory {
  id: number;
  name: string;
  code: string;
}

export interface Transaction {
  id: number;
  business: number;
  business_name: string;
  kind: "income" | "expense";
  category: number | null;
  category_name: string | null;
  amount: string;
  method: "cash" | "transfer";
  status: "pending" | "confirmed" | "void";
  confirmed_by: number | null;
  confirmed_by_name: string;
  created_by: number | null;
  created_by_name: string;
  occurred_at: string;
  note: string;
  created_at: string;
}

export interface TransactionFilters {
  page?: number;
  business?: number | "";
  kind?: string;
  status?: string;
  method?: string;
  category?: number | "";
  date_from?: string;
  date_to?: string;
}

export interface TransactionCreateInput {
  business: number;
  kind: "income" | "expense";
  category?: number | null;
  amount: string;
  method: "cash" | "transfer";
  occurred_at?: string;
  note?: string;
}

export interface ProfitReport {
  businesses: {
    business_id: number;
    business_name: string;
    income: string;
    expense: string;
    profit: string;
  }[];
  total: { income: string; expense: string; profit: string };
}

const cleanParams = (filters: object) =>
  Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== "" && v !== undefined && v !== null),
  );

export function useTransactions(filters: TransactionFilters = {}) {
  return useQuery({
    queryKey: ["transactions", filters],
    queryFn: async () =>
      (
        await api.get<Paginated<Transaction>>("/finance/transactions/", {
          params: cleanParams(filters),
        })
      ).data,
  });
}

export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: async () =>
      (await api.get<ExpenseCategory[]>("/finance/categories/")).data,
    staleTime: 5 * 60_000,
  });
}

export function useProfit(params: { business?: number | ""; date_from?: string; date_to?: string } = {}) {
  return useQuery({
    queryKey: ["profit", params],
    queryFn: async () =>
      (await api.get<ProfitReport>("/finance/profit", { params: cleanParams(params) })).data,
  });
}

function useInvalidateFinance() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: ["transactions"] });
    void qc.invalidateQueries({ queryKey: ["profit"] });
  };
}

export function useCreateTransaction() {
  const invalidate = useInvalidateFinance();
  return useMutation({
    mutationFn: async (input: TransactionCreateInput) =>
      (await api.post<Transaction>("/finance/transactions/", input)).data,
    onSuccess: invalidate,
  });
}

export function useConfirmIncome() {
  const invalidate = useInvalidateFinance();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<Transaction>(`/finance/transactions/${id}/confirm/`)).data,
    onSuccess: invalidate,
  });
}

export function useVoidTransaction() {
  const invalidate = useInvalidateFinance();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<Transaction>(`/finance/transactions/${id}/void/`)).data,
    onSuccess: invalidate,
  });
}

export function useDeleteTransaction() {
  const invalidate = useInvalidateFinance();
  return useMutation({
    mutationFn: async (id: number) => api.delete(`/finance/transactions/${id}/`),
    onSuccess: invalidate,
  });
}
