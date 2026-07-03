import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, tokenStorage } from "@/shared/api";

import type { Me } from "./types";

export function useMe(enabled = true) {
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => (await api.get<Me>("/me")).data,
    enabled: enabled && Boolean(tokenStorage.access),
    staleTime: 5 * 60_000,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (creds: { email: string; password: string }) => {
      const { data } = await api.post<{ access: string; refresh: string }>(
        "/auth/token",
        creds,
      );
      tokenStorage.set(data.access, data.refresh);
      const me = await api.get<Me>("/me");
      return me.data;
    },
    onSuccess: (me) => {
      qc.setQueryData(["me"], me);
    },
  });
}

export function logout() {
  tokenStorage.clear();
  window.location.assign("/login");
}
