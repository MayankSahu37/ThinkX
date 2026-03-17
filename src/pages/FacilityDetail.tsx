import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { ArrowLeft, MapPin, Building2, AlertTriangle, Droplets, TrendingUp, Zap, ShieldAlert } from 'lucide-react'
import { facilityService } from '../services/api'
import type { Facility } from '../utils/types'
import XAIPanel from '../components/XAIPanel'

export default function FacilityDetail() {
    const { id } = useParams()
    const [facility, setFacility] = useState<Facility | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        if (!id) return
        facilityService.getById(decodeURIComponent(id)).then(d => { setFacility(d || null); setLoading(false) })
    }, [id])

    if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500 border-t-transparent rounded-full animate-spin" /></div>
    if (!facility) return <div className="text-center py-20"><p className="text-lg font-semibold text-surface-700 mb-2">Facility Not Found</p><Link to="/facilities" className="text-sm text-primary-600">← Back</Link></div>

    const rc: Record<string, string> = { High: '#ef4444', Medium: '#f97316', Low: '#22c55e' }
    const riskColor = rc[facility.risk_level] || '#64748b'
    const crsPercent = Math.round(facility.crs * 100)

    // Multi-risk breakdown for bar chart
    const riskBreakdown = [
        { name: 'Flood', prob: facility.flood_risk_prob, label: facility.flood_risk_label, color: '#3b82f6' },
        { name: 'Water\nShortage', prob: facility.water_shortage_risk_prob, label: facility.water_shortage_risk_label, color: '#06b6d4' },
        { name: 'Power\nOutage', prob: facility.power_outage_risk_prob, label: facility.power_outage_risk_label, color: '#f97316' },
        { name: 'Sanitation\nFailure', prob: facility.sanitation_failure_risk_prob, label: facility.sanitation_failure_risk_label, color: '#8b5cf6' },
    ]

    const riskBarData = riskBreakdown.map(r => ({
        name: r.name,
        probability: Math.round((r.prob || 0) * 100),
        label: r.label,
    }))

    const getBarColor = (prob: number) => {
        if (prob >= 66) return '#ef4444'
        if (prob >= 33) return '#f97316'
        return '#22c55e'
    }

    // Environmental quick stats
    const envStats = [
        { label: 'GWL Depth', value: `${Number(facility.gwl_value).toFixed(1)} m`, icon: Droplets, color: 'blue' },
        { label: 'Rainfall', value: `${Number(facility.rainfall_value).toFixed(1)} mm`, icon: Droplets, color: 'cyan' },
        { label: 'River Level', value: `${Number(facility.river_level_value).toFixed(1)} m`, icon: TrendingUp, color: 'emerald' },
        { label: '24h Outage', value: `${(Number(facility.pred_outage_prob_24h) * 100).toFixed(0)}%`, icon: Zap, color: 'orange' },
    ]

    const address = [facility.complete_address, facility.street_address, facility['addr:city'], facility['addr:state'], facility['addr:postcode']]
        .filter(Boolean)
        .join(', ')

    return (
        <div className="space-y-6 max-w-6xl">
            <Link to="/facilities" className="inline-flex items-center gap-1.5 text-sm font-medium text-surface-500 hover:text-surface-700 transition">
                <ArrowLeft className="w-4 h-4" /> Back to Facilities
            </Link>

            {/* Header Card */}
            <div className="bg-white rounded-2xl border border-surface-200/60 p-6 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                    <div className="p-3 rounded-xl shrink-0" style={{ backgroundColor: `${riskColor}15` }}>
                        <Building2 className="w-7 h-7" style={{ color: riskColor }} />
                    </div>
                    <div className="flex-1 min-w-0">
                        <h1 className="text-2xl font-bold text-surface-900">{facility.facility_name}</h1>
                        <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-surface-500">
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${facility.facility_type === 'School' ? 'bg-blue-50 text-blue-700' : 'bg-purple-50 text-purple-700'}`}>{facility.facility_type}</span>
                            <span className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" /> {facility.district}</span>
                            <span className="text-surface-300">•</span>
                            <span>{Number(facility.latitude).toFixed(4)}, {Number(facility.longitude).toFixed(4)}</span>
                        </div>
                        {address && (
                            <p className="text-xs text-surface-400 mt-1">{address}</p>
                        )}
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="text-right">
                            <p className="text-xs text-surface-400 font-medium uppercase tracking-wider">CRS</p>
                            <p className="text-3xl font-bold" style={{ color: riskColor }}>{crsPercent}</p>
                        </div>
                        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-bold text-white" style={{ backgroundColor: riskColor }}>
                            {facility.risk_level} Risk
                        </span>
                    </div>
                </div>
            </div>

            {/* Info Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="bg-white rounded-2xl border border-surface-200/60 p-5 shadow-sm">
                    <h3 className="text-sm font-semibold text-surface-700 mb-4 flex items-center gap-2"><Building2 className="w-4 h-4 text-primary-500" /> Facility Info</h3>
                    <dl className="space-y-3">
                        {([
                            ['Name', facility.facility_name],
                            ['Type', facility.facility_type],
                            ['District', facility.district],
                            ['Alert Level', facility.alert_level],
                            ['Coords', `${Number(facility.latitude).toFixed(4)}, ${Number(facility.longitude).toFixed(4)}`],
                            ['Last Updated', facility.last_updated || 'N/A'],
                        ] as [string, string][]).map(([l, v]) => (
                            <div key={l} className="flex justify-between text-sm"><dt className="text-surface-500">{l}</dt><dd className="font-medium text-surface-800 text-right">{v}</dd></div>
                        ))}
                    </dl>
                </div>
                <div className="bg-white rounded-2xl border border-surface-200/60 p-5 shadow-sm">
                    <h3 className="text-sm font-semibold text-surface-700 mb-4 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-amber-500" /> Risk Analysis</h3>
                    <div className="space-y-4">
                        <div>
                            <div className="flex justify-between text-sm mb-1.5"><span className="text-surface-500">CRS</span><span className="font-bold" style={{ color: riskColor }}>{crsPercent}/100</span></div>
                            <div className="w-full h-3 rounded-full bg-surface-100 overflow-hidden"><div className="h-full rounded-full" style={{ width: `${crsPercent}%`, backgroundColor: riskColor }} /></div>
                        </div>
                        <div>
                            <p className="text-xs font-semibold text-surface-600 uppercase tracking-wider mb-2">Top Risk</p>
                            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200/60">
                                <ShieldAlert className="w-4 h-4 text-amber-600" />
                                <span className="text-sm font-semibold text-amber-800 capitalize">{facility.top_risk_type?.replace(/_/g, ' ') || 'N/A'}</span>
                                <span className="text-xs font-medium text-amber-600">{(facility.top_risk_score * 100).toFixed(0)}%</span>
                            </div>
                        </div>
                        <div>
                            <p className="text-xs font-semibold text-surface-600 uppercase tracking-wider mb-2">Sub-component Scores</p>
                            <ul className="space-y-2">
                                {[
                                    ['Water Availability', facility.water_availability],
                                    ['Flood Safety', facility.flood_safety],
                                    ['Rainfall Stability', facility.rainfall_stability],
                                    ['Electricity Reliability', facility.electricity_reliability],
                                ].map(([label, val]) => (
                                    <li key={label as string} className="flex items-center justify-between text-sm text-surface-700">
                                        <span>{label as string}</span>
                                        <span className="font-semibold">{((val as number) * 100).toFixed(0)}%</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
                <div className="bg-white rounded-2xl border border-surface-200/60 p-5 shadow-sm">
                    <h3 className="text-sm font-semibold text-surface-700 mb-4 flex items-center gap-2"><TrendingUp className="w-4 h-4 text-emerald-500" /> Environmental Stats</h3>
                    <div className="grid grid-cols-2 gap-3">
                        {envStats.map(s => (
                            <div key={s.label} className={`p-3 bg-${s.color}-50 rounded-xl text-center`}>
                                <s.icon className={`w-5 h-5 text-${s.color}-500 mx-auto mb-1`} />
                                <p className={`text-lg font-bold text-${s.color}-700`}>{s.value}</p>
                                <p className={`text-[10px] text-${s.color}-600 font-medium uppercase`}>{s.label}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Multi-Risk Bar Chart */}
            <div className="bg-white rounded-2xl border border-surface-200/60 p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-surface-700 mb-4 flex items-center gap-2"><ShieldAlert className="w-4 h-4 text-red-500" /> Multi-Risk Breakdown</h3>
                <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={riskBarData} layout="vertical" margin={{ left: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748b' }} unit="%" />
                        <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} width={90} />
                        <Tooltip
                            contentStyle={{
                                borderRadius: '12px',
                                border: '1px solid #e2e8f0',
                                boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                                fontSize: '13px',
                            }}
                            formatter={(value: any) => [`${value}%`, 'Probability']}
                        />
                        <Bar
                            dataKey="probability"
                            radius={[0, 6, 6, 0]}
                            name="Risk Probability"
                            fill="#3b82f6"
                            label={{ position: 'right', fontSize: 12, fill: '#64748b', formatter: (v: any) => `${v}%` }}
                        >
                            {riskBarData.map((entry, i) => (
                                <Bar key={i} dataKey="probability" fill={getBarColor(entry.probability)} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* XAI Panel Integration */}
            <div className="mt-6">
                <XAIPanel facilityId={facility.facility_id} />
            </div>
        </div>
    )
}
