/**
 * Shared domain types for Gruvle Leak's frontend.
 *
 * These mirror the Python worker's domain model (see worker/app/db/schema.py
 * and the worker's detection/scoring modules) so that wiring the real API in
 * is a matter of pointing fetches at live endpoints, not reshaping data.
 *
 * IMPORTANT: no business logic (calculations, detection, scoring) lives here
 * or anywhere in web/ — this is purely the shape of data that crosses the
 * wire from the worker.
 */

export type LeakCategory =
  | "UNBILLED"
  | "PRICING"
  | "INVOICE"
  | "RENEWAL"
  | "INVENTORY"
  | "DISCOUNT"
  | "REFUND"
  | "CUSTOMER"
  | "CONTRACT"
  | "OPERATIONS";

export type Confidence = "HIGH" | "MEDIUM" | "LOW";

export type FindingStatus = "NEW" | "REVIEWING" | "CONFIRMED" | "DISMISSED" | "RESOLVED";

export type ScanStage =
  | "UPLOADING"
  | "PROFILING"
  | "MAPPING"
  | "DETECTING"
  | "SCORING"
  | "GENERATING_REPORT"
  | "COMPLETED"
  | "FAILED";

export type CurrencyCode = "INR" | "USD" | "EUR" | "GBP" | "AED" | "SGD" | "AUD" | "CAD";

export type Industry =
  | "saas"
  | "agency"
  | "consulting"
  | "restaurant"
  | "hospitality"
  | "retail"
  | "logistics"
  | "service_business"
  | "distributor"
  | "small_manufacturer"
  | "other";

export interface FinancialImpact {
  impact_type: string;
  amount: number;
  currency: CurrencyCode;
  is_recurring: boolean;
  recurrence_period?: string | null;
}

export interface FindingEvidence {
  id: string;
  dataset_id: string;
  row_index: number;
  display_fields: Record<string, string | number | boolean | null>;
}

export interface FindingCalculation {
  method: string;
  formula: string;
  inputs?: Record<string, unknown>;
  result: number;
}

export interface Finding {
  id: string;
  scan_id: string;
  business_id: string;
  title: string;
  summary: string;
  category: LeakCategory;
  confidence: Confidence;
  confidence_explanation?: string | null;
  why_it_matters?: string | null;
  what_we_dont_know?: string[];
  recommended_action?: string | null;
  financial_impact: FinancialImpact;
  priority_score: number;
  status: FindingStatus;
  evidence: FindingEvidence[];
  calculation: FindingCalculation | null;
  created_at: string;
}

export interface Scan {
  id: string;
  business_id: string;
  stage: ScanStage;
  progress_percent: number;
  progress_detail?: string | null;
  records_analyzed: number;
  data_quality_score?: number | null;
  total_potential_leakage: number;
  total_high_confidence_leakage: number;
  finding_count: number;
  currency: CurrencyCode;
  error_message?: string | null;
  created_at: string;
}

export interface Business {
  id: string;
  owner_user_id: string;
  team_id: string;
  name: string;
  industry?: Industry | null;
  currency: CurrencyCode;
  business_model?: string | null;
  avg_order_value?: number | null;
  billing_frequency?: string | null;
  fiscal_year_start_month?: number | null;
  plan: "free" | "starter" | "growth" | "business";
}

export type ReportFormat = "pdf" | "csv" | "json" | "markdown";

export interface Report {
  id: string;
  scan_id: string;
  business_id: string;
  format: ReportFormat;
  storage_file_id?: string | null;
  summary?: Record<string, unknown> | null;
}
