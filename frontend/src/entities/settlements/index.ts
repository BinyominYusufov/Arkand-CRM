import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type Paginated } from "@/shared/api";

export interface Transfer {
  id: number;
  from_business: number;
  from_business_name: string;
  to_business: number;
  to_business_name: string;
  amount: string;
  status: "pending" | "approved" | "rejected";
  requires_owner_approval: boolean;
  note: string;
  created_by_name: string;
  approved_by_name: string;
  created_at: string;
}

export interface DebtSettlement {
  id: number;
  debt: number;
  method: "offset" | "return";
  amount: string;
  barter: number | null;
  note: string;
  created_at: string;
}

export interface Debt {
  id: number;
  debtor: number;
  debtor_name: string;
  creditor: number;
  creditor_name: string;
  amount: string;
  remaining: string;
  status: "open" | "closed";
  is_overdue: boolean;
  source_transfer: number | null;
  settlements: DebtSettlement[];
  created_at: string;
  closed_at: string | null;
}

export interface DebtsRegistry {
  debts: {
    id: number;
    debtor_id: number;
    debtor_name: string;
    creditor_id: number;
    creditor_name: string;
    amount: string;
    remaining: string;
    is_overdue: boolean;
    created_at: string;
    source_transfer_id: number | null;
  }[];
  pairs: {
    debtor_id: number;
    debtor_name: string;
    creditor_id: number;
    creditor_name: string;
    total_remaining: string;
    debts_count: number;
  }[];
  total_open: string;
}

export interface Barter {
  id: number;
  business_a: number;
  business_a_name: string;
  business_b: number;
  business_b_name: string;
  description: string;
  value: string;
  controlled_by: number | null;
  controlled_by_name: string;
  status: "active" | "completed" | "cancelled";
  created_at: string;
}

const clean = (params: Record<string, unknown>) =>
  Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== "" && v !== undefined && v !== null),
  );

export function useTransfers(params: { status?: string; page?: number } = {}) {
  return useQuery({
    queryKey: ["transfers", params],
    queryFn: async () =>
      (await api.get<Paginated<Transfer>>("/settlements/transfers/", { params: clean(params) })).data,
  });
}

export function useDebts(params: { status?: string; page?: number } = {}) {
  return useQuery({
    queryKey: ["debts", params],
    queryFn: async () =>
      (await api.get<Paginated<Debt>>("/settlements/debts/", { params: clean(params) })).data,
  });
}

export function useDebtsRegistry() {
  return useQuery({
    queryKey: ["debts-registry"],
    queryFn: async () =>
      (await api.get<DebtsRegistry>("/settlements/debts/registry/")).data,
  });
}

export function useBarters(params: { status?: string } = {}) {
  return useQuery({
    queryKey: ["barters", params],
    queryFn: async () =>
      (await api.get<Paginated<Barter>>("/settlements/barters/", { params: clean(params) })).data,
  });
}

function useInvalidateSettlements() {
  const qc = useQueryClient();
  return () => {
    for (const key of ["transfers", "debts", "debts-registry", "barters"]) {
      void qc.invalidateQueries({ queryKey: [key] });
    }
  };
}

export function useCreateTransfer() {
  const invalidate = useInvalidateSettlements();
  return useMutation({
    mutationFn: async (input: {
      from_business: number;
      to_business: number;
      amount: string;
      note?: string;
    }) => (await api.post<Transfer>("/settlements/transfers/", input)).data,
    onSuccess: invalidate,
  });
}

export function useApproveTransfer() {
  const invalidate = useInvalidateSettlements();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<Transfer>(`/settlements/transfers/${id}/approve/`)).data,
    onSuccess: invalidate,
  });
}

export function useRejectTransfer() {
  const invalidate = useInvalidateSettlements();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<Transfer>(`/settlements/transfers/${id}/reject/`)).data,
    onSuccess: invalidate,
  });
}

export function useSettleDebt() {
  const invalidate = useInvalidateSettlements();
  return useMutation({
    mutationFn: async (input: {
      id: number;
      method: "offset" | "return";
      amount?: string;
      note?: string;
    }) =>
      (
        await api.post<Debt>(`/settlements/debts/${input.id}/settle/`, {
          method: input.method,
          amount: input.amount || null,
          note: input.note ?? "",
        })
      ).data,
    onSuccess: invalidate,
  });
}

export function useNetDebts() {
  const invalidate = useInvalidateSettlements();
  return useMutation({
    mutationFn: async (input: { business_a: number; business_b: number }) =>
      (await api.post("/settlements/net", input)).data,
    onSuccess: invalidate,
  });
}

export function useCreateBarter() {
  const invalidate = useInvalidateSettlements();
  return useMutation({
    mutationFn: async (input: {
      business_a: number;
      business_b: number;
      description: string;
      value: string;
      controlled_by: number;
    }) => (await api.post<Barter>("/settlements/barters/", input)).data,
    onSuccess: invalidate,
  });
}

export function useBarterAction() {
  const invalidate = useInvalidateSettlements();
  return useMutation({
    mutationFn: async (input: {
      id: number;
      action: "complete" | "cancel" | "close-debt";
      debt?: number;
    }) =>
      (
        await api.post(
          `/settlements/barters/${input.id}/${input.action}/`,
          input.action === "close-debt" ? { debt: input.debt } : {},
        )
      ).data,
    onSuccess: invalidate,
  });
}
