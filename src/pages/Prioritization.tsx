import { useState, useMemo, useEffect } from 'react'
import {
    AlertTriangle, ArrowUpDown, Building2, ChevronDown, ChevronUp,
    Droplets, MapPin, Search, Shield, ShieldAlert, TrendingUp,
    Users, Waves, Zap, Filter,
} from 'lucide-react'
import { facilityService } from '../services/api'
import type { Facility } from '../utils/types'

// ── Priority scoring ──────────────────────────────────────────────────────────
interface PrioritizedFacility {
    facility: Facility
    priorityScore: number
    priorityLevel: 'High' | 'Moderate' | 'Low'
    disruptionProb: number
    crsInverse: number
    populationFactor: number
    envExposure: number
}

function computePriority(f: Facility, allFacilities: Facility[]): PrioritizedFacility {
    // 1. Disruption probability — max of all risk types (0-1)
    const disruptionProb = Math.max(
        f.flood_risk_prob || 0,
        f.water_shortage_risk_prob || 0,
        f.power_outage_risk_prob || 0,
        f.sanitation_failure_risk_prob || 0,
    )

    // 2. CRS inverse — lower resilience = higher priority (0-1)
    const crsInverse = 1 - (f.crs || 0.5)

    // 3. Population proxy — hospitals serve more critical populations
    //    Use outage probability as a proxy for facility importance/size
    const basePopFactor = f.facility_type === 'School' ? 0.6 : 0.85
    // Facilities with higher baseline outage risk tend to be larger/more critical
    const outageWeight = Math.min(1, (f.pred_outage_prob_24h || 0) + (f.pred_outage_prob_7d || 0) * 0.3)
    const populationFactor = Math.min(1, basePopFactor + outageWeight * 0.3)

    // 4. Environmental exposure — combined normalized environmental stress (0-1)
    const allRiver = allFacilities.map(x => Number(x.river_level_value) || 0)
    const allRain = allFacilities.map(x => Number(x.rainfall_value) || 0)
    const allGwl = allFacilities.map(x => Math.abs(Number(x.gwl_value) || 0))

    const norm = (val: number, arr: number[]) => {
        const mn = Math.min(...arr), mx = Math.max(...arr)
        return mx === mn ? 0.5 : (val - mn) / (mx - mn)
    }

    const riverNorm = norm(Number(f.river_level_value) || 0, allRiver)
    const rainNorm = norm(Number(f.rainfall_value) || 0, allRain)
    const gwlNorm = norm(Math.abs(Number(f.gwl_value) || 0), allGwl)
    const envExposure = riverNorm * 0.4 + rainNorm * 0.3 + gwlNorm * 0.3

    // Weighted priority score
    const priorityScore = (
        disruptionProb * 0.35 +
        crsInverse * 0.20 +
        populationFactor * 0.25 +
        envExposure * 0.20
    )

    const priorityLevel: 'High' | 'Moderate' | 'Low' =
        priorityScore >= 0.60 ? 'High' : priorityScore >= 0.38 ? 'Moderate' : 'Low'

    return {
        facility: f,
        priorityScore,
        priorityLevel,
        disruptionProb,
        crsInverse,
        populationFactor,
        envExposure,
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const levelColor = {
    High: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', dot: 'bg-red-500', badge: 'bg-red-100 text-red-700' },
    Moderate: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', dot: 'bg-amber-500', badge: 'bg-amber-100 text-amber-700' },
    Low: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200', dot: 'bg-green-500', badge: 'bg-green-100 text-green-700' },
}

function ScoreBar({ value, color }: { value: number; color: string }) {
    return (
        <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all duration-500" style={{ width: `${Math.round(value * 100)}%`, backgroundColor: color }} />
        </div>
    )
}

type SortKey = 'priority' | 'disruption' | 'crs' | 'population' | 'env' | 'name'

// ── Component ─────────────────────────────────────────────────────────────────
export default function Prioritization() {
    const [facilities, setFacilities] = useState<Facility[]>([])
    const [loading, setLoading] = useState(true)
    const [searchTerm, setSearchTerm] = useState('')
    const [filterLevel, setFilterLevel] = useState<'All' | 'High' | 'Moderate' | 'Low'>('All')
    const [sortKey, setSortKey] = useState<SortKey>('priority')
    const [sortAsc, setSortAsc] = useState(false)
    const [expandedId, setExpandedId] = useState<string | null>(null)

    useEffect(() => {
        facilityService.getAll().then(data => { setFacilities(data); setLoading(false) })
    }, [])

    const prioritized = useMemo(() => {
        return facilities.map(f => computePriority(f, facilities))
    }, [facilities])

    const filtered = useMemo(() => {
        let list = prioritized
        if (filterLevel !== 'All') list = list.filter(p => p.priorityLevel === filterLevel)
        if (searchTerm) {
            const q = searchTerm.toLowerCase()
            list = list.filter(p =>
                p.facility.facility_name.toLowerCase().includes(q) ||
                p.facility.district.toLowerCase().includes(q)
            )
        }
        // Sort
        list = [...list].sort((a, b) => {
            let cmp = 0
            switch (sortKey) {
                case 'priority': cmp = a.priorityScore - b.priorityScore; break
                case 'disruption': cmp = a.disruptionProb - b.disruptionProb; break
                case 'crs': cmp = a.crsInverse - b.crsInverse; break
                case 'population': cmp = a.populationFactor - b.populationFactor; break
                case 'env': cmp = a.envExposure - b.envExposure; break
                case 'name': cmp = a.facility.facility_name.localeCompare(b.facility.facility_name); break
            }
            return sortAsc ? cmp : -cmp
        })
        return list
    }, [prioritized, filterLevel, searchTerm, sortKey, sortAsc])

    const counts = useMemo(() => ({
        high: prioritized.filter(p => p.priorityLevel === 'High').length,
        moderate: prioritized.filter(p => p.priorityLevel === 'Moderate').length,
        low: prioritized.filter(p => p.priorityLevel === 'Low').length,
    }), [prioritized])

    const handleSort = (key: SortKey) => {
        if (sortKey === key) setSortAsc(!sortAsc)
        else { setSortKey(key); setSortAsc(false) }
    }

    const SortIcon = ({ k }: { k: SortKey }) => {
        if (sortKey !== k) return <ArrowUpDown className="w-3 h-3 text-slate-300" />
        return sortAsc ? <ChevronUp className="w-3 h-3 text-blue-500" /> : <ChevronDown className="w-3 h-3 text-blue-500" />
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[60vh]">
                <div className="w-8 h-8 border-3 border-violet-500 border-t-transparent rounded-full animate-spin" />
            </div>
        )
    }

    return (
        <div className="max-w-7xl mx-auto space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-surface-800 flex items-center gap-2">
                    <TrendingUp className="w-6 h-6 text-primary-500" />
                    Impact-Based Infrastructure Prioritization
                </h1>
                <p className="text-sm text-surface-500 mt-1">
                    Ranked facilities by vulnerability and societal impact to guide resource allocation decisions.
                </p>
            </div>

            {/* Summary cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {([
                    { label: 'High Priority', count: counts.high, level: 'High' as const, icon: AlertTriangle, desc: 'Immediate attention required' },
                    { label: 'Moderate Priority', count: counts.moderate, level: 'Moderate' as const, icon: ShieldAlert, desc: 'Monitor and prepare interventions' },
                    { label: 'Low Priority', count: counts.low, level: 'Low' as const, icon: Shield, desc: 'Standard monitoring' },
                ]).map(c => {
                    const lc = levelColor[c.level]
                    const isActive = filterLevel === c.level
                    return (
                        <button
                            key={c.level}
                            onClick={() => setFilterLevel(filterLevel === c.level ? 'All' : c.level)}
                            className={`text-left p-5 rounded-2xl border transition-all shadow-sm ${isActive ? `${lc.bg} ${lc.border} ring-2 ring-offset-1 ring-${c.level === 'High' ? 'red' : c.level === 'Moderate' ? 'amber' : 'green'}-300` : 'bg-white border-slate-200/60 hover:border-slate-300'}`}
                        >
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                    <div className={`w-2.5 h-2.5 rounded-full ${lc.dot}`} />
                                    <span className={`text-sm font-semibold ${isActive ? lc.text : 'text-slate-700'}`}>{c.label}</span>
                                </div>
                                <c.icon className={`w-4 h-4 ${isActive ? lc.text : 'text-slate-400'}`} />
                            </div>
                            <p className={`text-3xl font-bold ${isActive ? lc.text : 'text-slate-800'}`}>{c.count}</p>
                            <p className="text-xs text-slate-400 mt-1">{c.desc}</p>
                        </button>
                    )
                })}
            </div>

            {/* Toolbar */}
            <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
                <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input type="text" placeholder="Search by name or district…" value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                        className="w-full pl-9 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-sm" />
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-500">
                    <Filter className="w-3.5 h-3.5" />
                    Showing {filtered.length} of {prioritized.length} facilities
                    {filterLevel !== 'All' && (
                        <button onClick={() => setFilterLevel('All')} className="ml-1 text-blue-500 hover:text-blue-700 font-semibold">
                            (clear filter)
                        </button>
                    )}
                </div>
            </div>

            {/* Table */}
            <div className="bg-white border border-slate-200/60 rounded-2xl shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-100">
                                <th className="text-left px-5 py-3 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                                    <button onClick={() => handleSort('name')} className="flex items-center gap-1 hover:text-slate-800">
                                        Rank / Facility <SortIcon k="name" />
                                    </button>
                                </th>
                                <th className="text-center px-3 py-3 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                                    <button onClick={() => handleSort('priority')} className="flex items-center gap-1 mx-auto hover:text-slate-800">
                                        Priority <SortIcon k="priority" />
                                    </button>
                                </th>
                                <th className="text-center px-3 py-3 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                                    <button onClick={() => handleSort('disruption')} className="flex items-center gap-1 mx-auto hover:text-slate-800">
                                        Disruption <SortIcon k="disruption" />
                                    </button>
                                </th>
                                <th className="text-center px-3 py-3 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                                    <button onClick={() => handleSort('crs')} className="flex items-center gap-1 mx-auto hover:text-slate-800">
                                        Vulnerability <SortIcon k="crs" />
                                    </button>
                                </th>
                                <th className="text-center px-3 py-3 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                                    <button onClick={() => handleSort('population')} className="flex items-center gap-1 mx-auto hover:text-slate-800">
                                        Pop. Impact <SortIcon k="population" />
                                    </button>
                                </th>
                                <th className="text-center px-3 py-3 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                                    <button onClick={() => handleSort('env')} className="flex items-center gap-1 mx-auto hover:text-slate-800">
                                        Env. Exposure <SortIcon k="env" />
                                    </button>
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {filtered.map((p, idx) => {
                                const lc = levelColor[p.priorityLevel]
                                const expanded = expandedId === p.facility.facility_id
                                return (
                                    <tr key={p.facility.facility_id}
                                        className={`transition-colors cursor-pointer ${expanded ? lc.bg : 'hover:bg-slate-50/50'}`}
                                        onClick={() => setExpandedId(expanded ? null : p.facility.facility_id)}>

                                        {/* Rank + Name */}
                                        <td className="px-5 py-3">
                                            <div className="flex items-center gap-3">
                                                <span className="text-xs font-bold text-slate-400 w-6 text-right">#{idx + 1}</span>
                                                <div className="min-w-0">
                                                    <p className="font-semibold text-slate-800 truncate">{p.facility.facility_name}</p>
                                                    <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
                                                        <span className="flex items-center gap-0.5"><Building2 className="w-3 h-3" />{p.facility.facility_type}</span>
                                                        <span className="flex items-center gap-0.5"><MapPin className="w-3 h-3" />{p.facility.district}</span>
                                                    </div>
                                                    {expanded && (
                                                        <div className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 text-[11px]">
                                                            <span className="text-slate-500 flex items-center gap-1"><Waves className="w-3 h-3" />Flood: <b className="text-slate-700">{(p.facility.flood_risk_prob * 100).toFixed(0)}%</b></span>
                                                            <span className="text-slate-500 flex items-center gap-1"><Droplets className="w-3 h-3" />Water: <b className="text-slate-700">{(p.facility.water_shortage_risk_prob * 100).toFixed(0)}%</b></span>
                                                            <span className="text-slate-500 flex items-center gap-1"><Zap className="w-3 h-3" />Power: <b className="text-slate-700">{(p.facility.power_outage_risk_prob * 100).toFixed(0)}%</b></span>
                                                            <span className="text-slate-500 flex items-center gap-1"><ShieldAlert className="w-3 h-3" />Sanit: <b className="text-slate-700">{(p.facility.sanitation_failure_risk_prob * 100).toFixed(0)}%</b></span>
                                                            <span className="text-slate-500 flex items-center gap-1"><Shield className="w-3 h-3" />CRS: <b className="text-slate-700">{(p.facility.crs * 100).toFixed(0)}/100</b></span>
                                                            <span className="text-slate-500 flex items-center gap-1"><Users className="w-3 h-3" />Top Risk: <b className="text-slate-700 capitalize">{p.facility.top_risk_type?.replace(/_/g, ' ')}</b></span>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </td>

                                        {/* Priority Score */}
                                        <td className="px-3 py-3 text-center">
                                            <span className={`inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full ${lc.badge}`}>
                                                <span className={`w-1.5 h-1.5 rounded-full ${lc.dot}`} />
                                                {(p.priorityScore * 100).toFixed(0)}
                                            </span>
                                        </td>

                                        {/* Disruption */}
                                        <td className="px-3 py-3">
                                            <div className="w-20 mx-auto space-y-1">
                                                <span className="text-xs font-semibold text-slate-600 block text-center">{(p.disruptionProb * 100).toFixed(0)}%</span>
                                                <ScoreBar value={p.disruptionProb} color={p.disruptionProb >= 0.6 ? '#ef4444' : p.disruptionProb >= 0.35 ? '#f97316' : '#22c55e'} />
                                            </div>
                                        </td>

                                        {/* Vulnerability (CRS inverse) */}
                                        <td className="px-3 py-3">
                                            <div className="w-20 mx-auto space-y-1">
                                                <span className="text-xs font-semibold text-slate-600 block text-center">{(p.crsInverse * 100).toFixed(0)}%</span>
                                                <ScoreBar value={p.crsInverse} color={p.crsInverse >= 0.6 ? '#ef4444' : p.crsInverse >= 0.35 ? '#f97316' : '#22c55e'} />
                                            </div>
                                        </td>

                                        {/* Population Impact */}
                                        <td className="px-3 py-3">
                                            <div className="w-20 mx-auto space-y-1">
                                                <span className="text-xs font-semibold text-slate-600 block text-center">{(p.populationFactor * 100).toFixed(0)}%</span>
                                                <ScoreBar value={p.populationFactor} color={p.populationFactor >= 0.7 ? '#ef4444' : p.populationFactor >= 0.5 ? '#f97316' : '#22c55e'} />
                                            </div>
                                        </td>

                                        {/* Environmental Exposure */}
                                        <td className="px-3 py-3">
                                            <div className="w-20 mx-auto space-y-1">
                                                <span className="text-xs font-semibold text-slate-600 block text-center">{(p.envExposure * 100).toFixed(0)}%</span>
                                                <ScoreBar value={p.envExposure} color={p.envExposure >= 0.6 ? '#ef4444' : p.envExposure >= 0.35 ? '#f97316' : '#22c55e'} />
                                            </div>
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Methodology note */}
            <div className="bg-slate-50 border border-slate-200/60 rounded-xl p-4 text-xs text-slate-500 leading-relaxed">
                <p className="font-semibold text-slate-600 mb-1">Scoring Methodology</p>
                <p>
                    Priority Score = Disruption Probability (35%) + Vulnerability i.e. 1−CRS (20%) + Population Impact (25%) + Environmental Exposure (20%).
                    Facilities are ranked with <strong>High Priority</strong> (≥60), <strong>Moderate</strong> (38–59), and <strong>Low</strong> (&lt;38).
                    Hospitals receive a higher population impact weight than schools. Click any row to expand details.
                </p>
            </div>
        </div>
    )
}
