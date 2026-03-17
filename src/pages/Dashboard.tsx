import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
    PieChart, Pie, Cell,
    AreaChart, Area,
} from 'recharts'
import {
    Building2, AlertTriangle, ShieldAlert, ShieldCheck,
    TrendingUp, ArrowUpRight,
} from 'lucide-react'
import ForecastPanel from '../components/ForecastPanel'
import { facilityService, riskService } from '../services/api'
import type { Facility, DashboardSummary, ClimateTrend, DistrictData } from '../utils/types'

const RISK_COLORS = { High: '#ef4444', Medium: '#f97316', Low: '#22c55e' }

function SummaryCard({ title, value, icon: Icon, color, trend }: {
    title: string; value: number; icon: React.ElementType; color: string; trend?: string
}) {
    return (
        <div className="relative overflow-hidden bg-white rounded-2xl border border-surface-200/60 p-5 shadow-sm hover:shadow-md transition-shadow duration-300 group">
            <div className="flex items-start justify-between">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-surface-400 mb-1">{title}</p>
                    <p className="text-3xl font-bold text-surface-900">{value}</p>
                    {trend && (
                        <span className="inline-flex items-center gap-1 mt-2 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                            <TrendingUp className="w-3 h-3" /> {trend}
                        </span>
                    )}
                </div>
                <div className={`p-3 rounded-xl transition-transform duration-300 group-hover:scale-110`} style={{ backgroundColor: `${color}15` }}>
                    <Icon className="w-6 h-6" style={{ color }} />
                </div>
            </div>
            <div className="absolute bottom-0 left-0 right-0 h-1 opacity-80" style={{ background: `linear-gradient(90deg, ${color}, transparent)` }} />
        </div>
    )
}

export default function Dashboard() {
    const [summary, setSummary] = useState<DashboardSummary | null>(null)
    const [facilities, setFacilities] = useState<Facility[]>([])
    const [trends, setTrends] = useState<ClimateTrend[]>([])
    const [districts, setDistricts] = useState<DistrictData[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        async function load() {
            const [s, f, t, d] = await Promise.all([
                riskService.getSummary(),
                facilityService.getAll(),
                riskService.getClimateTrends(),
                riskService.getDistrictData(),
            ])
            setSummary(s)
            setFacilities(f)
            setTrends(t)
            setDistricts(d)
            setLoading(false)
        }
        load()
    }, [])

    // Build monthly climate chart from environmental_daily data
    const climateChartData = useMemo(() => {
        if (!trends.length) return []
        // Group by month, pivot metrics
        const months: Record<string, Record<string, number>> = {}
        for (const t of trends) {
            if (!months[t.month]) months[t.month] = {}
            months[t.month][t.metric] = t.value
        }
        return Object.entries(months)
            .sort(([a], [b]) => a.localeCompare(b))
            .slice(-12)
            .map(([month, vals]) => ({
                month: month.slice(5), // "2024-01" → "01"
                rainfall: Math.abs(vals['rainfall'] ?? 0),
                gwl: Math.abs(vals['gwl'] ?? 0),
                river: Math.abs(vals['river_level'] ?? 0),
            }))
    }, [trends])

    if (loading || !summary) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="w-8 h-8 border-3 border-primary-500 border-t-transparent rounded-full animate-spin" />
            </div>
        )
    }

    const pieData = [
        { name: 'High', value: summary.high },
        { name: 'Medium', value: summary.medium },
        { name: 'Low', value: summary.low },
    ]

    const highRiskFacilities = facilities
        .filter(f => f.risk_level === 'High')
        .sort((a, b) => (b.top_risk_score ?? b.crs) - (a.top_risk_score ?? a.crs))
        .slice(0, 10)

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-surface-900">Dashboard</h1>
                <p className="text-sm text-surface-500 mt-1">Real-time overview of infrastructure climate risks — Raipur District</p>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                <SummaryCard title="Total Facilities" value={summary.total} icon={Building2} color="#3b82f6" />
                <SummaryCard title="High Risk" value={summary.high} icon={ShieldAlert} color={RISK_COLORS.High} />
                <SummaryCard title="Medium Risk" value={summary.medium} icon={AlertTriangle} color={RISK_COLORS.Medium} />
                <SummaryCard title="Low Risk" value={summary.low} icon={ShieldCheck} color={RISK_COLORS.Low} />
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Risk Distribution Pie Chart */}
                <div className="bg-white rounded-2xl border border-surface-200/60 p-5 shadow-sm">
                    <h3 className="text-sm font-semibold text-surface-700 mb-4">Risk Distribution</h3>
                    <ResponsiveContainer width="100%" height={220}>
                        <PieChart>
                            <Pie
                                data={pieData}
                                cx="50%"
                                cy="50%"
                                innerRadius={55}
                                outerRadius={85}
                                paddingAngle={4}
                                dataKey="value"
                                strokeWidth={0}
                            >
                                {pieData.map((entry) => (
                                    <Cell key={entry.name} fill={RISK_COLORS[entry.name as keyof typeof RISK_COLORS]} />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{
                                    borderRadius: '12px',
                                    border: '1px solid #e2e8f0',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                                    fontSize: '13px',
                                }}
                            />
                            <Legend
                                verticalAlign="bottom"
                                formatter={(value: string) => <span className="text-xs text-surface-600 ml-1">{value}</span>}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                </div>

                {/* Facilities by District */}
                <div className="bg-white rounded-2xl border border-surface-200/60 p-5 shadow-sm">
                    <h3 className="text-sm font-semibold text-surface-700 mb-4">Facilities by District</h3>
                    <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={districts} barGap={2}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                            <XAxis dataKey="district" tick={{ fontSize: 11, fill: '#64748b' }} angle={-20} textAnchor="end" height={50} />
                            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                            <Tooltip
                                contentStyle={{
                                    borderRadius: '12px',
                                    border: '1px solid #e2e8f0',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                                    fontSize: '13px',
                                }}
                            />
                            <Bar dataKey="schools" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Schools" />
                            <Bar dataKey="hospitals" fill="#8b5cf6" radius={[4, 4, 0, 0]} name="Hospitals" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* Climate Trend */}
                <div className="bg-white rounded-2xl border border-surface-200/60 p-5 shadow-sm">
                    <h3 className="text-sm font-semibold text-surface-700 mb-4">Environmental Trend (Monthly)</h3>
                    <ResponsiveContainer width="100%" height={220}>
                        <AreaChart data={climateChartData}>
                            <defs>
                                <linearGradient id="colorRain" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                </linearGradient>
                                <linearGradient id="colorGwl" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
                                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                            <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#64748b' }} />
                            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                            <Tooltip
                                contentStyle={{
                                    borderRadius: '12px',
                                    border: '1px solid #e2e8f0',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                                    fontSize: '13px',
                                }}
                            />
                            <Area type="monotone" dataKey="rainfall" stroke="#3b82f6" fill="url(#colorRain)" strokeWidth={2} name="Rainfall (mm)" />
                            <Area type="monotone" dataKey="gwl" stroke="#ef4444" fill="url(#colorGwl)" strokeWidth={2} name="GWL Depth (m)" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* 7-Day Climate Risk Forecast */}
            <div className="min-h-[600px]">
                <ForecastPanel />
            </div>
        </div>
    )
}
