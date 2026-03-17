import axios from 'axios'
import type { Facility, Alert, ClimateTrend, DistrictData, DashboardSummary, XAIExplanation, ForecastData } from '../utils/types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
    baseURL: API_BASE,
    timeout: 15000,
    headers: { 'Content-Type': 'application/json' },
})

export const facilityService = {
    getAll: async (): Promise<Facility[]> => {
        const { data } = await api.get('/api/facilities')
        return data
    },

    getById: async (id: string): Promise<Facility | undefined> => {
        try {
            const { data } = await api.get(`/api/facilities/${id}`)
            return data
        } catch {
            return undefined
        }
    },
}

export const riskService = {
    getSummary: async (): Promise<DashboardSummary> => {
        const { data } = await api.get('/api/risk-summary')
        return data
    },

    getClimateTrends: async (): Promise<ClimateTrend[]> => {
        const { data } = await api.get('/api/climate-trends')
        return data
    },

    getDistrictData: async (): Promise<DistrictData[]> => {
        const { data } = await api.get('/api/district-data')
        return data
    },
}

export const alertService = {
    getAll: async (): Promise<Alert[]> => {
        const { data } = await api.get('/api/alerts')
        return data
    },
}

export const weatherService = {
    getCurrent: async () => {
        const { data } = await api.get('/api/weather')
        return data
    },
}

export const xaiService = {
    getExplanation: async (facilityId: string): Promise<XAIExplanation | null> => {
        try {
            const { data } = await api.get(`/api/facilities/${encodeURIComponent(facilityId)}/explain`)
            return data
        } catch {
            return null
        }
    },
}

export const forecastService = {
    get7DayForecast: async (facilityId: string): Promise<ForecastData> => {
        const { data } = await api.get(`/api/forecast/${encodeURIComponent(facilityId)}`)
        return data
    },
}

export default api
