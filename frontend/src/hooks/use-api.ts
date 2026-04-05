"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export function useAuths() {
  return useQuery({
    queryKey: ["auths"],
    queryFn: () => apiFetch<unknown[]>("/api/v1/auths"),
  });
}

export function usePolicys() {
  return useQuery({
    queryKey: ["policys"],
    queryFn: () => apiFetch<unknown[]>("/api/v1/policys"),
  });
}

export function useClaimss() {
  return useQuery({
    queryKey: ["claimss"],
    queryFn: () => apiFetch<unknown[]>("/api/v1/claimss"),
  });
}

export function useUsers() {
  return useQuery({
    queryKey: ["users"],
    queryFn: () => apiFetch<unknown[]>("/api/v1/users"),
  });
}

export function useNotifications() {
  return useQuery({
    queryKey: ["notifications"],
    queryFn: () => apiFetch<unknown[]>("/api/v1/notifications"),
  });
}

export function useDocuments() {
  return useQuery({
    queryKey: ["documents"],
    queryFn: () => apiFetch<unknown[]>("/api/v1/documents"),
  });
}
