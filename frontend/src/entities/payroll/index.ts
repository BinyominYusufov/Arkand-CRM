import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type Paginated } from "@/shared/api";

export interface Employee {
  id: number;
  full_name: string;
  business: number | null;
  business_name: string | null;
  position: string;
  salary_type: "objective" | "administrative";
  is_salesperson: boolean;
  is_active: boolean;
}

export interface SalaryScheme {
  id: number;
  employee: number;
  employee_name: string;
  scheme_type: "fixed" | "percent_of_sales" | "per_unit_tiered";
  config: Record<string, unknown>;
  is_active: boolean;
}

export interface PayrollItem {
  id: number;
  employee: number;
  employee_name: string;
  business_name: string | null;
  salary_type: string;
  base: string;
  bonus: string;
  total: string;
  breakdown: Record<string, unknown>;
}

export interface PayrollRun {
  id: number;
  year: number;
  month: number;
  status: "draft" | "finalized";
  paid_from_hq: boolean;
  created_at: string;
  finalized_at: string | null;
  total_fund: string;
  items_count: number;
  items?: PayrollItem[];
}

const clean = (params: Record<string, unknown>) =>
  Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== "" && v !== undefined && v !== null),
  );

export function useEmployees(params: { is_active?: boolean; page?: number } = {}) {
  return useQuery({
    queryKey: ["employees", params],
    queryFn: async () =>
      (await api.get<Paginated<Employee>>("/payroll/employees/", { params: clean(params) })).data,
  });
}

export function useSchemes(params: { employee?: number } = {}) {
  return useQuery({
    queryKey: ["schemes", params],
    queryFn: async () =>
      (await api.get<Paginated<SalaryScheme>>("/payroll/schemes/", { params: clean(params) })).data,
  });
}

export function usePayrollRuns() {
  return useQuery({
    queryKey: ["payroll-runs"],
    queryFn: async () =>
      (await api.get<Paginated<PayrollRun>>("/payroll/runs/")).data,
  });
}

export function usePayrollRun(id: number | null) {
  return useQuery({
    queryKey: ["payroll-run", id],
    queryFn: async () => (await api.get<PayrollRun>(`/payroll/runs/${id}/`)).data,
    enabled: id != null,
  });
}

export function useRunPayroll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { year: number; month: number }) =>
      (await api.post<PayrollRun>("/payroll/runs/", input)).data,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["payroll-runs"] });
      void qc.invalidateQueries({ queryKey: ["payroll-run"] });
    },
  });
}

export function useFinalizeRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await api.post<PayrollRun>(`/payroll/runs/${id}/finalize/`)).data,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["payroll-runs"] });
      void qc.invalidateQueries({ queryKey: ["payroll-run"] });
    },
  });
}
