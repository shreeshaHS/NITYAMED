/** Typed REST client for NityaMed FastAPI backend with automatic JWT refresh. */

import { tokenStore } from './tokenStore';
import type {
  AdherenceReport,
  AdminCatalogueListItem,
  AdminHealthMetrics,
  AdminTestEmailResponse,
  AssistantResponse,
  AuthMeResponse,
  CatalogueItem,
  DailyDoseItem,
  FrequencyType,
  InventorySummaryItem,
  MedicineEducation,
  NotificationItem,
  PersonalMedicine,
  PersonalMedicineDetail,
  ProfileResponse,
  RefillPredictionItem,
  StockTransactionItem,
  SupportedLang,
  SyncBootstrapResponse,
  TokenResponse,
} from '../types/api';

const API_BASE =
  process.env.EXPO_PUBLIC_API_URL?.replace(/\/+$/, '') || 'http://127.0.0.1:8000/api/v1';

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function tryRefreshTokens(): Promise<string | null> {
  const refresh = await tokenStore.getRefreshToken();
  if (!refresh) return null;
  try {
    const resp = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!resp.ok) {
      await tokenStore.clearSession();
      return null;
    }
    const data = (await resp.json()) as TokenResponse;
    if (data.access_token && data.refresh_token) {
      await tokenStore.saveTokens(data.access_token, data.refresh_token);
    }
    return data.access_token;
  } catch {
    return null;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  auth = true,
  allowRetry = true
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };

  if (auth) {
    const token = await tokenStore.getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (resp.status === 401 && auth && allowRetry) {
    const refreshed = await tryRefreshTokens();
    if (refreshed) {
      return request<T>(path, options, auth, false);
    }
  }

  if (resp.status === 204) {
    return undefined as T;
  }

  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const err = body?.error;
    throw new ApiError(
      resp.status,
      err?.code || 'REQUEST_FAILED',
      err?.message || `Request failed (${resp.status})`
    );
  }
  return body as T;
}

export const api = {
  register(payload: {
    email: string;
    password: string;
    display_name: string;
    preferred_lang: SupportedLang;
  }) {
    return request<TokenResponse>('/auth/register', { method: 'POST', body: JSON.stringify(payload) }, false);
  },

  login(payload: { email: string; password: string }) {
    return request<TokenResponse>('/auth/login', { method: 'POST', body: JSON.stringify(payload) }, false);
  },

  verifyEmail(payload: { email: string; otp_code: string }) {
    return request<TokenResponse>('/auth/verify-email', { method: 'POST', body: JSON.stringify(payload) }, false);
  },

  resendVerification(email: string) {
    return request<{ already_verified: boolean; email_sent: boolean; dev_otp_preview?: string | null }>(
      '/auth/resend-verification',
      { method: 'POST', body: JSON.stringify({ email }) },
      false
    );
  },

  forgotPassword(email: string) {
    return request<{ message: string; email_sent: boolean; dev_otp_preview?: string | null }>(
      '/auth/forgot-password',
      { method: 'POST', body: JSON.stringify({ email }) },
      false
    );
  },

  resetPassword(payload: { email: string; otp_code: string; new_password: string }) {
    return request<void>('/auth/reset-password', { method: 'POST', body: JSON.stringify(payload) }, false);
  },

  getMe() {
    return request<AuthMeResponse>('/auth/me');
  },

  logout(refresh_token: string) {
    return request<void>('/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token }) });
  },

  getProfile() {
    return request<ProfileResponse>('/profile');
  },

  updateProfile(payload: Partial<ProfileResponse>) {
    return request<ProfileResponse>('/profile', { method: 'PATCH', body: JSON.stringify(payload) });
  },

  exportData() {
    return request<Record<string, unknown>>('/profile/export');
  },

  deleteAccount(password: string) {
    return request<void>('/profile', {
      method: 'DELETE',
      body: JSON.stringify({ password }),
    });
  },

  searchCatalogue(q: string, form?: string, manufacturer?: string) {
    const params = new URLSearchParams({ q, limit: '25' });
    if (form) params.set('form', form);
    if (manufacturer && manufacturer.trim()) params.set('manufacturer', manufacturer.trim());
    return request<CatalogueItem[]>(`/catalogue/search?${params.toString()}`);
  },

  requestCatalogueVerification(payload: {
    brand_name: string;
    generic_name?: string | null;
    strength: string;
    dosage_form: string;
    manufacturer?: string | null;
    standard_pack_size?: string | null;
  }) {
    return request<CatalogueItem>('/catalogue/requests', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getCatalogueEducation(catalogueId: string) {
    return request<MedicineEducation>(`/catalogue/${catalogueId}/education`);
  },

  listMedicines(status?: string) {
    const query = status && status !== 'all' ? `?status=${encodeURIComponent(status)}` : '';
    return request<PersonalMedicine[]>(`/medicines${query}`);
  },

  createMedicine(payload: Record<string, unknown>) {
    return request<PersonalMedicine>('/medicines', { method: 'POST', body: JSON.stringify(payload) });
  },

  getMedicineDetail(medId: string) {
    return request<PersonalMedicineDetail>(`/medicines/${medId}`);
  },

  updateMedicine(medId: string, payload: Record<string, unknown>) {
    return request<PersonalMedicine>(`/medicines/${medId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  createSchedule(
    medId: string,
    payload: {
      frequency_type: FrequencyType;
      times: Array<{ time: string; dose: string }>;
      weekdays?: number[];
      interval_days?: number;
      start_date: string;
      end_date?: string | null;
      horizon_days?: number;
    }
  ) {
    return request(`/medicines/${medId}/schedules`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getDailyDoses(dateStr: string) {
    return request<DailyDoseItem[]>(`/doses/daily?date=${encodeURIComponent(dateStr)}`);
  },

  confirmDose(doseId: string, actual_qty: string, client_event_id: string) {
    return request(`/doses/${doseId}/confirm`, {
      method: 'POST',
      body: JSON.stringify({
        actual_qty,
        actioned_at: new Date().toISOString(),
        client_event_id,
      }),
    });
  },

  skipDose(doseId: string, client_event_id: string) {
    return request(`/doses/${doseId}/skip`, {
      method: 'POST',
      body: JSON.stringify({ client_event_id }),
    });
  },

  snoozeDose(doseId: string, minutes = 15) {
    return request(`/doses/${doseId}/snooze`, {
      method: 'POST',
      body: JSON.stringify({ minutes }),
    });
  },

  correctDose(doseId: string, new_status: string, new_qty: string, reason: string) {
    return request(`/doses/${doseId}/correct`, {
      method: 'POST',
      body: JSON.stringify({ new_status, new_qty, reason }),
    });
  },

  getInventorySummary(horizonDays = 14) {
    return request<InventorySummaryItem[]>(`/inventory/summary?horizon_days=${horizonDays}`);
  },

  purchaseStock(medId: string, packs: number, loose_units: string, client_event_id: string) {
    return request(`/inventory/${medId}/purchase`, {
      method: 'POST',
      body: JSON.stringify({ packs, loose_units, client_event_id }),
    });
  },

  adjustStock(
    medId: string,
    tx_type: 'MANUAL_ADJUSTMENT' | 'EXPIRED_DAMAGED_LOST',
    qty_delta: string,
    notes: string,
    client_event_id: string
  ) {
    return request(`/inventory/${medId}/adjust`, {
      method: 'POST',
      body: JSON.stringify({ tx_type, qty_delta, notes, client_event_id }),
    });
  },

  listStockTransactions(medId: string) {
    return request<StockTransactionItem[]>(`/inventory/${medId}/transactions?limit=30`);
  },

  reconcileStock(medId: string, actual_counted_stock: string, client_event_id: string) {
    return request(`/inventory/${medId}/reconcile`, {
      method: 'POST',
      body: JSON.stringify({ actual_counted_stock, client_event_id }),
    });
  },

  getRefillPredictions() {
    return request<RefillPredictionItem[]>('/refills/predictions');
  },

  getAdherenceReport(days = 30) {
    return request<AdherenceReport>(`/analytics/adherence?days=${days}`);
  },

  askAssistantText(text: string, language_hint: SupportedLang) {
    return request<AssistantResponse>('/assistant/text', {
      method: 'POST',
      body: JSON.stringify({ text, language_hint }),
    });
  },

  confirmAssistantAction(confirmation_token: string, approved: boolean) {
    return request<AssistantResponse>('/assistant/confirm', {
      method: 'POST',
      body: JSON.stringify({ confirmation_token, approved }),
    });
  },

  syncBootstrap() {
    return request<SyncBootstrapResponse>('/sync/bootstrap');
  },

  syncEvents(events: Array<Record<string, unknown>>) {
    return request<{ applied_count: number; duplicate_count: number; rejected_count: number }>(
      '/sync/events',
      { method: 'POST', body: JSON.stringify({ events }) }
    );
  },

  adminGetMetrics() {
    return request<AdminHealthMetrics>('/admin/health/metrics');
  },

  adminListCatalogue(q = '', statusFilter: 'all' | 'active' | 'deprecated' | 'unverified' = 'all') {
    return request<AdminCatalogueListItem[]>(
      `/admin/catalogue?q=${encodeURIComponent(q)}&status_filter=${statusFilter}&limit=50`
    );
  },

  adminUpdateCatalogue(catalogueId: string, payload: Record<string, unknown>) {
    return request(`/admin/catalogue/${catalogueId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  adminCreateCatalogue(payload: Record<string, unknown>) {
    return request('/admin/catalogue', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  adminSeedCatalogue() {
    return request<{ inserted: number }>('/admin/catalogue/seed', { method: 'POST' });
  },

  adminRunMaintenanceSweep() {
    return request<{ expired_doses_marked: number; refill_alerts_created: number }>(
      '/admin/maintenance/sweep',
      { method: 'POST' }
    );
  },

  adminTestEmail(recipient_email: string) {
    return request<AdminTestEmailResponse>('/admin/system/test-email', {
      method: 'POST',
      body: JSON.stringify({ recipient_email }),
    });
  },

  getNotificationHistory(limit = 30) {
    return request<NotificationItem[]>(`/notifications/history?limit=${limit}`);
  },

  checkRefillAlerts() {
    return request<NotificationItem[]>('/notifications/refills/check', { method: 'POST' });
  },

  updateNotificationStatus(notifId: string, delivery_status: 'delivered' | 'dismissed' | 'failed') {
    return request<NotificationItem>(`/notifications/${notifId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ delivery_status }),
    });
  },
};
