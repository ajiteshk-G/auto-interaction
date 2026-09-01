export interface VehicleVariant {
  name: string;
  price_ex_showroom: string;
  engine_or_battery: string;
  transmission: string;
  key_features: string[];
}

export interface VehicleItem {
  id: string;
  name: string;
  tagline: string;
  category: string;
  price_range: string;
  hero_image: string;
  image_url?: string;
  engine_specs: string;
  seating_capacity: string;
  fuel_or_battery: string;
  range_or_mileage: string;
  key_highlights: string[];
  usp: string;
  variants: VehicleVariant[];
  is_custom_source_of_truth?: boolean;
  uploaded_image_url?: string;
}

export interface BrandSummary {
  id: string;
  name: string;
  tagline: string;
  logo_url: string;
  primary_color: string;
  vehicle_count: number;
  is_active: boolean;
}

export interface BrandCatalog {
  id: string;
  name: string;
  tagline: string;
  logo_url: string;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  avatar_name: string;
  agent_name?: string;
  avatar_voice: string;
  source_urls: string[];
  is_active: boolean;
  vehicles: VehicleItem[];
  dealerships: DealershipItem[];
}

export interface BrandOnboardRequest {
  brand_name: string;
  urls: string[];
}

export interface VehicleUpdateRequest {
  name?: string;
  tagline?: string;
  category?: string;
  price_range?: string;
  hero_image?: string;
  engine_specs?: string;
  seating_capacity?: string;
  fuel_or_battery?: string;
  range_or_mileage?: string;
  key_highlights?: string[];
  usp?: string;
  variants?: VehicleVariant[];
}

export interface DealershipItem {
  id: string;
  name: string;
  address: string;
  city: string;
  phone: string;
  rating: number;
  available_advisors: string[];
  has_test_drive_home_pickup: boolean;
}

export interface CustomerProfile {
  id: number;
  customer_id: string;
  name: string;
  phone: string;
  email?: string;
  city: string;
  preferred_language: string;
  current_phase: string;
  interested_vehicle_id: string;
  interested_variant: string;
  budget_range: string;
  owned_vin?: string;
  owned_vehicle_name?: string;
  registration_number?: string;
  odometer_km: number;
  insurance_policy_number?: string;
  insurance_type?: string;
}

// Stage 2: Sales Mobile App & Test Ride Insights
export interface TestRideLeadItem {
  customer_id: string;
  name: string;
  phone: string;
  email?: string;
  city: string;
  preferred_vehicle: string;
  vehicle_id?: string;
  variant?: string;
  booking_reference?: string;
  dealership_id?: string;
  dealership_name?: string;
  booking_type?: string;
  delivery_address?: string;
  booking_status: string;
  scheduled_slot?: string;
  presales_notes?: string;
  advisor_checklist?: string[];
  is_custom_checklist?: boolean;
}

export interface TestRideInsightResponse {
  session_id: string;
  customer_id: string;
  vehicle_id: string;
  vehicle_name: string;
  sales_advisor_name: string;
  gcs_uri: string;
  gcs_bucket: string;
  duration_seconds: number;
  transcript: string;
  customer_sentiment_score: number;
  purchase_intent_score: number;
  loved_features: string[];
  objections_raised: string[];
  advisor_pitch_score: number;
  advisor_coaching_feedback: string;
  recommended_action: string;
  status: string;
  created_at: string;
}

// Stage 3: Outbound Call & Insights
export interface OutboundDialogueTurnResponse {
  call_reference: string;
  speaker: string;
  agent_message: string;
  ai_reply?: string;
  audio_tts_url?: string;
  is_call_finished: boolean;
  action_item?: string;
  turn_index: number;
}

export interface OutboundCallInsightsResponse {
  call_reference: string;
  customer_id: string;
  customer_name: string;
  agent_name: string;
  phone_number: string;
  call_status: string;
  call_duration_seconds: number;
  transcript: string;
  objections_handled: string[];
  objection_resolution_status: string;
  customer_sentiment: string;
  customer_decision: string;
  locked_vehicle_variant: string;
  locked_allocation_days: number;
  next_step: string;
  created_at: string;
}
