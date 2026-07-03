import { useQuery } from "@tanstack/react-query";

import { api } from "@/shared/api";

export interface Business {
  id: number;
  name: string;
  code: string;
  kind: string;
  kind_display: string;
  is_active: boolean;
}

export function useBusinesses() {
  return useQuery({
    queryKey: ["businesses"],
    queryFn: async () => (await api.get<Business[]>("/businesses/")).data,
    staleTime: 5 * 60_000,
  });
}
