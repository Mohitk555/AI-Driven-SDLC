const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ApiError {
  detail: string;
  status: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  full_name: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "user" | "admin";
}

export interface Claim {
  id: string;
  policy_number: string;
  claim_type: "auto" | "health" | "property" | "life";
  description: string;
  amount: number;
  status: ClaimStatus;
  admin_notes: string | null;
  created_at: string;
  updated_at: string;
  user_id: string;
  user_name?: string;
}

export type ClaimStatus =
  | "submitted"
  | "under_review"
  | "approved"
  | "rejected"
  | "info_required";

export interface CreateClaimRequest {
  policy_number: string;
  claim_type: string;
  description: string;
  amount: number;
}

export interface UpdateClaimRequest {
  status?: ClaimStatus;
  admin_notes?: string;
}

export interface Document {
  id: string;
  claim_id: string;
  filename: string;
  content_type: string;
  size: number;
  uploaded_at: string;
}

export interface ClaimsSummary {
  total: number;
  submitted: number;
  under_review: number;
  approved: number;
  rejected: number;
  info_required: number;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("auth_token");
}

async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("auth_token");
      window.location.href = "/login";
    }
    throw { detail: "Unauthorized", status: 401 } as ApiError;
  }

  if (!response.ok) {
    let detail = "An unexpected error occurred";
    try {
      const errorBody = await response.json();
      detail = errorBody.detail || detail;
    } catch {
      // response body not JSON
    }
    throw { detail, status: response.status } as ApiError;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ---- Auth ----

export async function login(data: LoginRequest): Promise<AuthResponse> {
  const formBody = new URLSearchParams();
  formBody.append("username", data.email);
  formBody.append("password", data.password);

  const response = await fetch(`${BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formBody,
  });

  if (!response.ok) {
    let detail = "Invalid credentials";
    try {
      const errorBody = await response.json();
      detail = errorBody.detail || detail;
    } catch {
      // ignore
    }
    throw { detail, status: response.status } as ApiError;
  }

  return response.json();
}

export async function register(data: RegisterRequest): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getMe(): Promise<User> {
  return apiFetch<User>("/api/v1/auth/me");
}

// ---- Claims ----

export async function getClaims(): Promise<Claim[]> {
  return apiFetch<Claim[]>("/api/v1/claims");
}

export async function getAllClaims(): Promise<Claim[]> {
  return apiFetch<Claim[]>("/api/v1/claims/all");
}

export async function getClaim(id: string): Promise<Claim> {
  return apiFetch<Claim>(`/api/v1/claims/${id}`);
}

export async function createClaim(data: CreateClaimRequest): Promise<Claim> {
  return apiFetch<Claim>("/api/v1/claims", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateClaim(
  id: string,
  data: UpdateClaimRequest
): Promise<Claim> {
  return apiFetch<Claim>(`/api/v1/claims/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function getClaimsSummary(): Promise<ClaimsSummary> {
  return apiFetch<ClaimsSummary>("/api/v1/claims/summary");
}

// ---- Documents ----

export async function uploadDocument(
  claimId: string,
  file: File
): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);

  return apiFetch<Document>(`/api/v1/claims/${claimId}/documents`, {
    method: "POST",
    body: formData,
  });
}

export async function getDocuments(claimId: string): Promise<Document[]> {
  return apiFetch<Document[]>(`/api/v1/claims/${claimId}/documents`);
}

export function getDocumentDownloadUrl(
  claimId: string,
  documentId: string
): string {
  return `${BASE_URL}/api/v1/claims/${claimId}/documents/${documentId}/download`;
}
