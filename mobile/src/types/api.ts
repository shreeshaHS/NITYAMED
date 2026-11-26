/** Shared TypeScript models aligned with NityaMed FastAPI /api/v1 responses. */

export type SupportedLang = 'en' | 'kn' | 'hi';

export type DosageForm =
  | 'tablet'
  | 'capsule'
  | 'syrup'
  | 'injection'
  | 'inhaler'
  | 'drops'
  | 'other';

export type DoseStatus =
  | 'pending'
  | 'snoozed'
  | 'taken_on_time'
  | 'taken_late'
  | 'explicitly_skipped'
  | 'partially_taken'
  | 'expired_unconfirmed';

export type FrequencyType =
  | 'once_daily'
  | 'multiple_daily'
  | 'alternate_day'
  | 'weekly'
  | 'selected_weekdays'
  | 'varying_dose'
  | 'fixed_course'
  | 'as_needed';

export interface TokenResponse {
  access_token: string | null;
  refresh_token: string | null;
  token_type: string;
  expires_in: number;
  verification_required?: boolean;
  email_sent?: boolean;
  dev_otp_preview?: string | null;
}

export interface AuthMeResponse {
  user_id: string;
  email: string;
  role: 'patient' | 'admin';
  is_email_verified: boolean;
}

export interface ProfileResponse {
  user_id: string;
  email: string;
  role: string;
  is_email_verified?: boolean;
  display_name: string;
  preferred_lang: SupportedLang;
  timezone: string;
  lockscreen_privacy: boolean;
  email_reminders_enabled: boolean;
  default_snooze_min: number;
  ontime_window_min: number;
  expiry_cutoff_hours: number;
  refill_alert_days: number;
  updated_at: string;
}

export interface CatalogueItem {
  id: string;
  brand_name: string;
  generic_name: string;
  active_ingredients: string | null;
  strength: string;
  dosage_form: DosageForm;
  standard_pack_size: string | null;
  pack_unit: string | null;
  manufacturer: string | null;
  is_verified: boolean;
}

export interface MedicineEducation {
  catalogue_id: string;
  category: string;
  common_uses: string;
  mechanism: string;
  side_effects: string;
  precautions: string;
  additional_notes: string | null;
  source_name: string;
  source_url: string | null;
  verified_at: string;
  disclaimer: string;
}

export interface PersonalMedicine {
  id: string;
  user_id: string;
  catalogue_id: string | null;
  is_custom: boolean;
  display_name: string;
  generic_name: string | null;
  strength: string;
  dosage_form: DosageForm;
  dose_per_intake: string;
  dose_unit: string;
  stock_unit: string;
  units_per_pack: string | null;
  confirmed_stock: string;
  low_stock_threshold: string | null;
  instructions: string | null;
  status: 'active' | 'paused' | 'completed' | 'archived';
}

export interface PersonalMedicineDetail {
  medicine: PersonalMedicine;
  education: MedicineEducation | null;
  education_notice: string | null;
}

export interface DailyDoseItem {
  id: string;
  personal_med_id: string;
  schedule_version_id: string;
  display_name: string;
  strength: string;
  dosage_form: string;
  dose_unit: string;
  instructions: string | null;
  confirmed_stock: string;
  scheduled_at: string;
  expected_qty: string;
  confirmed_qty: string;
  status: DoseStatus;
  snoozed_until: string | null;
  actioned_at: string | null;
}

export interface InventorySummaryItem {
  personal_med_id: string;
  display_name: string;
  stock_unit: string;
  confirmed_stock: string;
  projected_upcoming_consumption: string;
  projected_stock_balance: string;
  projection_horizon_days: number;
  is_estimate: boolean;
}

export interface RefillPredictionItem {
  personal_med_id: string;
  display_name: string;
  confirmed_stock: string;
  stock_unit: string;
  prediction_mode: string;
  estimated_remaining_days: number | null;
  projected_depletion_date: string | null;
  suggested_refill_alert_date: string | null;
  should_alert_now: boolean;
  reason: string;
}

export interface AdherenceReport {
  window_days: number;
  closed_scheduled_count: number;
  upcoming_pending_count: number;
  taken_on_time: number;
  taken_late: number;
  partially_taken: number;
  explicitly_skipped: number;
  expired_unconfirmed: number;
  confirmed_adherence_rate: number | null;
  on_time_rate: number | null;
  unconfirmed_rate: number | null;
  formula_notes: Record<string, string>;
  per_medicine: Array<{
    personal_med_id: string;
    display_name: string;
    closed_scheduled_count: number;
    taken_on_time: number;
    taken_late: number;
    partially_taken: number;
    explicitly_skipped: number;
    expired_unconfirmed: number;
    confirmed_adherence_rate: number | null;
    unconfirmed_rate: number | null;
  }>;
  irregular_patterns: string[];
  disclaimer: string;
}

export interface AssistantResponse {
  reply_text: string;
  transcript: string | null;
  language: SupportedLang;
  intent: string;
  confidence: number;
  classification_source: string;
  requires_confirmation: boolean;
  confirmation_token: string | null;
  proposed_action: Record<string, unknown> | null;
  tts_audio_base64: string | null;
  suggested_replies?: string[];
}

export interface AdminCatalogueListItem {
  id: string;
  brand_name: string;
  generic_name: string;
  strength: string;
  dosage_form: DosageForm;
  standard_pack_size: string | null;
  manufacturer: string | null;
  is_verified: boolean;
  is_deprecated: boolean;
}

export interface AdminHealthMetrics {
  total_users: number;
  verified_users: number;
  email_backup_opt_in_users: number;
  active_personal_medicines: number;
  total_dose_events: number;
  confirmed_dose_events: number;
  expired_unconfirmed_events: number;
  total_catalogue_items: number;
  verified_catalogue_items: number;
  deprecated_catalogue_items: number;
  total_notifications: number;
  smtp_configured: boolean;
  require_email_verification: boolean;
  ml_model_ready: boolean;
  ml_model_name: string | null;
}

export interface AdminTestEmailResponse {
  sent: boolean;
  detail: string;
}

export interface NotificationItem {
  id: string;
  personal_med_id: string | null;
  notif_type: 'dose_reminder' | 'low_stock' | 'refill_alert' | 'system';
  dedup_key: string;
  scheduled_for: string;
  sent_at: string | null;
  delivery_status: 'scheduled' | 'delivered' | 'dismissed' | 'failed';
  payload_preview: string;
  created_at: string;
}

export interface SyncBootstrapResponse {
  synced_at: string;
  medicines: PersonalMedicine[];
  active_schedules: Array<Record<string, unknown>>;
  dose_events: DailyDoseItem[];
}

export interface StockTransactionItem {
  id: string;
  personal_med_id: string;
  tx_type: string;
  qty_delta: string;
  balance_after: string;
  notes: string | null;
  created_at: string;
}
