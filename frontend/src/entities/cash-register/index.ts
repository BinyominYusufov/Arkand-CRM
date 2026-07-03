import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type Paginated } from "@/shared/api";

export interface CashRegister {
  id: number;
  name: string;
  business: number;
  business_name: string;
  turnover_limit: string;
  is_active: boolean;
  balance: string;
  month_turnover: string;
  limit_utilization: number;
  over_limit: boolean;
  members: number[];
}

export interface CashOperation {
  id: number;
  register: number;
  register_name: string;
  business_name: string;
  direction: "in" | "out";
  method: "cash" | "transfer";
  amount: string;
  note: string;
  created_by: number | null;
  created_by_name: string;
  occurred_at: string;
  created_at: string;
}

export interface CashOperationCreateInput {
  register: number;
  direction: "in" | "out";
  method: "cash" | "transfer";
  amount: string;
  note?: string;
}

export function useCashRegisters() {
  return useQuery({
    queryKey: ["cash-registers"],
    queryFn: async () => (await api.get<CashRegister[]>("/cash/registers/")).data,
  });
}

export function useCashOperations(
  params: { register?: number | ""; direction?: string; page?: number } = {},
) {
  return useQuery({
    queryKey: ["cash-operations", params],
    queryFn: async () =>
      (
        await api.get<Paginated<CashOperation>>("/cash/operations/", {
          params: Object.fromEntries(
            Object.entries(params).filter(([, v]) => v !== "" && v !== undefined),
          ),
        })
      ).data,
  });
}

export function useCreateCashOperation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: CashOperationCreateInput) =>
      (await api.post<CashOperation>("/cash/operations/", input)).data,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["cash-registers"] });
      void qc.invalidateQueries({ queryKey: ["cash-operations"] });
    },
  });
}
