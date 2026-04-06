import type {
  IQuoteCreateRequest,
  IQuoteResponse,
  IQuoteSummary,
  IPolicyResponse,
  IPolicySummary,
  IPaginatedResponse,
  IAdminPolicyListResponse,
  IPolicyActionResponse,
} from '@/lib/types/policy';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth_token');
}

async function authFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    let detail = 'An unexpected error occurred';
    try {
      const errorBody = await response.json();
      detail = errorBody.detail || detail;
    } catch {
      // response body not JSON
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export async function createQuote(
  data: IQuoteCreateRequest
): Promise<IQuoteResponse> {
  return authFetch<IQuoteResponse>('/api/v1/quotes', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getQuotes(
  page: number = 1
): Promise<IPaginatedResponse<IQuoteSummary>> {
  return authFetch<IPaginatedResponse<IQuoteSummary>>(
    `/api/v1/quotes?page=${page}`
  );
}

export async function getQuote(id: number): Promise<IQuoteResponse> {
  return authFetch<IQuoteResponse>(`/api/v1/quotes/${id}`);
}

export async function purchasePolicy(
  quoteId: number
): Promise<IPolicyResponse> {
  return authFetch<IPolicyResponse>(`/api/v1/quotes/${quoteId}/purchase`, {
    method: 'POST',
  });
}

export async function getPolicies(
  page: number = 1
): Promise<IPaginatedResponse<IPolicySummary>> {
  return authFetch<IPaginatedResponse<IPolicySummary>>(
    `/api/v1/policies?page=${page}`
  );
}

export async function getPolicy(id: number): Promise<IPolicyResponse> {
  return authFetch<IPolicyResponse>(`/api/v1/policies/${id}`);
}

export async function downloadPolicyDocument(id: number): Promise<Blob> {
  const token = getToken();
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(
    `${BASE_URL}/api/v1/policies/${id}/document`,
    { headers }
  );

  if (!response.ok) {
    throw new Error('Failed to download policy document');
  }

  return response.blob();
}

export async function getAdminPolicies(
  page: number = 1,
  status?: string,
  search?: string
): Promise<IAdminPolicyListResponse> {
  const params = new URLSearchParams({ page: page.toString(), pageSize: '20' });
  if (status) params.set('status', status);
  if (search) params.set('search', search);
  return authFetch<IAdminPolicyListResponse>(`/api/v1/admin/policies?${params}`);
}

export async function cancelPolicy(id: number, reason: string): Promise<IPolicyActionResponse> {
  return authFetch<IPolicyActionResponse>(`/api/v1/admin/policies/${id}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export async function renewPolicy(id: number): Promise<IPolicyActionResponse> {
  return authFetch<IPolicyActionResponse>(`/api/v1/admin/policies/${id}/renew`, {
    method: 'POST',
  });
}

export async function reinstatePolicy(id: number, reason: string): Promise<IPolicyActionResponse> {
  return authFetch<IPolicyActionResponse>(`/api/v1/admin/policies/${id}/reinstate`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}
