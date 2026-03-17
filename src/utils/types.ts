export interface Facility {
    facility_id: string
    facility_name: string
    facility_type: 'Hospital' | 'School'
    district: string
    latitude: number
    longitude: number

    // Composite Risk Score (0–1)
    crs: number
    risk_level: 'High' | 'Medium' | 'Low'

    // Environmental values
    gwl_value: number
    rainfall_value: number
    river_level_value: number

    // Outage risk predictions
    outage_risk: number
    pred_outage_prob_24h: number
    pred_outage_prob_7d: number

    // Sub-component scores (0–1)
    water_availability: number
    flood_safety: number
    rainfall_stability: number
    electricity_reliability: number

    // Multi-risk probabilities (0–1)
    flood_risk_prob: number
    water_shortage_risk_prob: number
    power_outage_risk_prob: number
    sanitation_failure_risk_prob: number

    // Multi-risk labels
    flood_risk_label: string
    water_shortage_risk_label: string
    power_outage_risk_label: string
    sanitation_failure_risk_label: string

    // Aggregate
    top_risk_type: string
    top_risk_score: number
    alert_flag: boolean
    alert_level: 'Critical' | 'High' | 'Normal'

    // Address info (may be empty)
    complete_address?: string
    street_address?: string
    'addr:city'?: string
    'addr:state'?: string
    'addr:postcode'?: string
    last_updated?: string
}

export interface Alert {
    id: string
    facilityId: string
    facilityName: string
    facilityType: string
    riskLevel: string
    topRiskType: string
    topRiskScore: number
    predictedIssue: string
    recommendedAction: string
    timestamp: string
}

export interface DashboardSummary {
    total: number
    high: number
    medium: number
    low: number
}

export interface DistrictData {
    district: string
    schools: number
    hospitals: number
}

export interface ClimateTrend {
    metric: string
    month: string
    value: number
}

export interface XAIFactor {
    factor: string
    key: string
    icon: string
    contribution: number
    contribution_pct: number
    raw_value: string
    direction: 'increases_risk' | 'decreases_risk'
}

export interface XAIExplanation {
    facility_id: string
    facility_name: string
    facility_type: string
    top_risk_type: string
    top_risk_label: string
    top_risk_score: number
    top_risk_score_pct: number
    confidence: number
    confidence_pct: number
    explanations: XAIFactor[]
}

export interface ForecastDay {
    facility_name: string
    date: string
    day: number
    flood_risk_probability: number
    water_shortage_probability: number
    power_outage_probability: number
    sanitation_failure_probability: number
    overall_risk_level: 'High' | 'Medium' | 'Low'
    overall_risk_probability: number
}

export interface ForecastData {
    facility_id: string
    facility_name: string
    forecast: ForecastDay[]
    ai_insight: string
}
