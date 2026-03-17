import { useState, useEffect, useMemo } from 'react'
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import {
    Droplets, Zap, Waves, ShieldAlert, AlertCircle, Info, Building2, ChevronDown
} from 'lucide-react'
import { forecastService, facilityService } from '../services/api'
import type { Facility, ForecastData, ForecastDay } from '../utils/types'

const RISK_LEVEL_COLORS = {
    Low: '#22c55e',
    Medium: '#f97316',
    High: '#ef4444',
}

interface FeatureCardProps {
    title: string
    probability: number
    level: string
    icon: React.ElementType
    color: string
}

function RiskIndicatorCard({ title, probability, level, icon: Icon, color }: FeatureCardProps) {
    return (
        <div className="bg-white rounded-xl border border-surface-200 p-4 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: `${color}15` }}>
                    <Icon className="w-5 h-5" style={{ color }} />
                </div>
                <h4 className="font-semibold text-surface-700">{title}</h4>
            </div>
            <div className="flex items-end justify-between">
                <div>
                    <p className="text-2xl font-bold text-surface-900">{(probability * 100).toFixed(0)}%</p>
                    <p className="text-xs text-surface-500">probability</p>
                </div>
                <span
                    className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                    style={{ backgroundColor: `${color}15`, color }}
                >
                    {level}
                </span>
            </div>
        </div>
    )
}

export default function ForecastPanel() {
    const [facilities, setFacilities] = useState<Facility[]>([])
    const [selectedFacility, setSelectedFacility] = useState<string>('')
    const [forecastData, setForecastData] = useState<ForecastData | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        async function loadFacilities() {
            const data = await facilityService.getAll()
            setFacilities(data)
            if (data.length > 0) {
                setSelectedFacility(data[0].facility_id)
            }
        }
        loadFacilities()
    }, [])

    useEffect(() => {
        if (!selectedFacility) return

        async function loadForecast() {
            setLoading(true)
            try {
                const data = await forecastService.get7DayForecast(selectedFacility)
                setForecastData(data)
            } catch (error) {
                console.error("Failed to load forecast:", error)
            } finally {
                setLoading(false)
            }
        }
        loadForecast()
    }, [selectedFacility])

    const chartData = useMemo(() => {
        if (!forecastData) return []
        return forecastData.forecast.map(d => ({
            day: `Day ${d.day}`,
            risk: d.overall_risk_probability,
            level: d.overall_risk_level,
            flood: d.flood_risk_probability,
            water: d.water_shortage_probability,
            power: d.power_outage_probability,
            sanitation: d.sanitation_failure_probability,
        }))
    }, [forecastData])

    // Find custom alert for high risk days
    const highRiskDay = useMemo(() => {
        return forecastData?.forecast.find(d => d.overall_risk_level === 'High')
    }, [forecastData])

    if (!forecastData && loading) {
        return (
            <div className="flex items-center justify-center h-96 bg-white rounded-2xl border border-dashed border-surface-300">
                <div className="w-8 h-8 border-3 border-primary-500 border-t-transparent rounded-full animate-spin" />
            </div>
        )
    }

    return (
        <div className="bg-white rounded-2xl border border-surface-200/60 shadow-sm overflow-hidden flex flex-col h-full">
            {/* Header with Selection */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between px-6 py-4 border-b border-surface-100 gap-4">
                <div>
                    <h3 className="text-lg font-bold text-surface-900">7-Day Climate Risk Forecast</h3>
                    <p className="text-sm text-surface-500">Anticipate disruptions with AI-driven predictive modeling</p>
                </div>

                <div className="relative group w-full sm:w-auto">
                    <label className="text-[10px] font-bold text-surface-400 uppercase tracking-widest absolute -top-2 left-2 px-1 bg-white z-10 transition-colors group-focus-within:text-primary-500">
                        Select Facility
                    </label>
                    <select
                        value={selectedFacility}
                        onChange={(e) => setSelectedFacility(e.target.value)}
                        className="appearance-none w-full sm:w-64 pl-4 pr-10 py-2.5 bg-surface-50 border border-surface-200 rounded-xl text-sm font-medium text-surface-700 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all cursor-pointer"
                    >
                        {facilities.map(f => (
                            <option key={f.facility_id} value={f.facility_id}>
                                {f.facility_name}
                            </option>
                        ))}
                    </select>
                    <ChevronDown className="w-4 h-4 text-surface-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none group-focus-within:text-primary-500 transition-colors" />
                </div>
            </div>

            <div className="p-6 space-y-8 flex-1 overflow-y-auto">
                {/* Visual Legend */}
                <div className="flex justify-center items-center gap-6">
                    {Object.entries(RISK_LEVEL_COLORS).map(([level, color]) => (
                        <div key={level} className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                            <span className="text-xs font-semibold text-surface-600">{level}</span>
                        </div>
                    ))}
                </div>

                {/* Trend Chart */}
                <div className="relative h-[240px] w-full">
                    {loading && (
                        <div className="absolute inset-0 z-10 bg-white/60 backdrop-blur-sm flex items-center justify-center">
                            <div className="w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
                        </div>
                    )}
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData}>
                            <defs>
                                <linearGradient id="forecastGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                            <XAxis
                                dataKey="day"
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: '#64748b', fontSize: 12 }}
                                dy={10}
                            />
                            <YAxis
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: '#64748b', fontSize: 12 }}
                                domain={[0, 1]}
                                ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
                                tickFormatter={(v) => `${(v * 100)}%`}
                            />
                            <Tooltip
                                content={({ active, payload, label }) => {
                                    if (active && payload && payload.length) {
                                        const data = payload[0].payload as any;
                                        const color = RISK_LEVEL_COLORS[data.level as keyof typeof RISK_LEVEL_COLORS];
                                        return (
                                            <div className="bg-white p-3 rounded-xl shadow-xl border border-surface-200 outline-none">
                                                <p className="text-xs font-bold text-surface-500 mb-2">{label}</p>
                                                <div className="flex items-center gap-2 mb-2">
                                                    <span className="text-lg font-bold text-surface-900">{(data.risk * 100).toFixed(0)}%</span>
                                                    <span
                                                        className="text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider"
                                                        style={{ backgroundColor: `${color}15`, color }}
                                                    >
                                                        {data.level}
                                                    </span>
                                                </div>
                                                <div className="space-y-1">
                                                    <div className="flex justify-between gap-4 text-[11px]">
                                                        <span className="text-surface-500">Flood</span>
                                                        <span className="font-semibold text-surface-700">{(data.flood * 100).toFixed(0)}%</span>
                                                    </div>
                                                    <div className="flex justify-between gap-4 text-[11px]">
                                                        <span className="text-surface-500">Water</span>
                                                        <span className="font-semibold text-surface-700">{(data.water * 100).toFixed(0)}%</span>
                                                    </div>
                                                </div>
                                            </div>
                                        )
                                    }
                                    return null;
                                }}
                            />
                            <Area
                                type="monotone"
                                dataKey="risk"
                                stroke="#8b5cf6"
                                strokeWidth={3}
                                fillOpacity={1}
                                fill="url(#forecastGradient)"
                                animationDuration={1000}
                                activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2, fill: '#8b5cf6' }}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>

                {/* Risk Insight Overview (Ref image lookalike) */}
                {forecastData && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        {/* Use Day 1 or current risk for static cards */}
                        <RiskIndicatorCard
                            title="Flood Risk"
                            probability={forecastData.forecast[0].flood_risk_probability}
                            level={forecastData.forecast[0].overall_risk_level}
                            icon={Waves}
                            color={RISK_LEVEL_COLORS.High}
                        />
                        <RiskIndicatorCard
                            title="Water Shortage"
                            probability={forecastData.forecast[0].water_shortage_probability}
                            level={forecastData.forecast[0].overall_risk_level}
                            icon={Droplets}
                            color={RISK_LEVEL_COLORS.Medium}
                        />
                        <RiskIndicatorCard
                            title="Power Outage"
                            probability={forecastData.forecast[0].power_outage_probability}
                            level={forecastData.forecast[0].overall_risk_level}
                            icon={Zap}
                            color={RISK_LEVEL_COLORS.Low}
                        />
                        <RiskIndicatorCard
                            title="Sanitation Failure"
                            probability={forecastData.forecast[0].sanitation_failure_probability}
                            level={forecastData.forecast[0].overall_risk_level}
                            icon={ShieldAlert}
                            color={RISK_LEVEL_COLORS.Medium}
                        />
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-surface-100">
                    {/* AI Insight Panel */}
                    <div className="bg-primary-50/40 rounded-2xl p-5 border border-primary-100/50">
                        <div className="flex items-center gap-2 mb-3">
                            <Info className="w-4 h-4 text-primary-600" />
                            <h4 className="text-sm font-bold text-primary-900 uppercase tracking-wider">AI Insight</h4>
                        </div>
                        <p className="text-sm text-surface-600 leading-relaxed font-medium italic">
                            "{forecastData?.ai_insight}"
                        </p>
                        <div className="mt-4 flex items-center gap-2 text-[11px] font-bold text-primary-700 bg-white/70 w-fit px-2 py-1 rounded-lg">
                            <Building2 className="w-3 h-3" />
                            Explainable AI Analysis
                        </div>
                    </div>

                    {/* Alert Indicator */}
                    <div className={`p-5 rounded-2xl border transition-all duration-500 flex flex-col justify-center ${highRiskDay
                            ? 'bg-red-50 border-red-100 animate-pulse-subtle'
                            : 'bg-emerald-50 border-emerald-100'
                        }`}>
                        <div className="flex items-start gap-4">
                            <div className={`p-2.5 rounded-xl ${highRiskDay ? 'bg-red-500/10' : 'bg-emerald-500/10'}`}>
                                {highRiskDay ? (
                                    <AlertCircle className="w-6 h-6 text-red-600" />
                                ) : (
                                    <ShieldAlert className="w-6 h-6 text-emerald-600" />
                                )}
                            </div>
                            <div>
                                <h4 className={`text-sm font-bold ${highRiskDay ? 'text-red-900' : 'text-emerald-900'} uppercase tracking-wider`}>
                                    {highRiskDay ? `Critical: High Risk on Day ${highRiskDay.day}` : 'Current System Status'}
                                </h4>
                                <p className={`text-sm mt-1 font-medium ${highRiskDay ? 'text-red-700' : 'text-emerald-700'}`}>
                                    {highRiskDay
                                        ? "Recommended Action: Inspect facility drainage systems and prepare backup power."
                                        : "All predicted risks are currently within manageable thresholds for the next 7 days."
                                    }
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
