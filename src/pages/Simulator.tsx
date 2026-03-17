import { useState, useMemo, useEffect } from 'react'
import {
    CloudRain, Thermometer, Activity, MapPin, AlertCircle,
    RefreshCw, Search, Building2, Check, Zap, Waves,
    Droplets, ShieldAlert,
} from 'lucide-react'
import { facilityService } from '../services/api'
import type { Facility } from '../utils/types'

// ── Per-facility simulation logic ─────────────────────────────────────────────
interface SimResult {
    name: string
    type: string
    district: string
    waterShortage: number
    floodRisk: number
    powerOutage: number
    sanitationFail: number
    topRisk: string
    topRiskPct: number
}

function simulateFacility(
    f: Facility,
    rainfall: number,
    temperature: number,
    pumpFailure: boolean,
    electricityFailure: boolean,
): SimResult {
    // Start from real baseline probabilities (0-1 scale → percentage)
    let water = (f.water_shortage_risk_prob || 0) * 100
    let flood = (f.flood_risk_prob || 0) * 100
    let power = (f.power_outage_risk_prob || 0) * 100
    let sanit = (f.sanitation_failure_risk_prob || 0) * 100

    // ── Rainfall → primarily FLOOD risk ──
    if (rainfall > 70) {
        flood += 30 + (rainfall - 70) * 0.8           // Heavy rain → severe flood spike
        sanit += 10                                    // Sanitation degrades from flooding
        power += 5                                     // Water damage to electrical systems
    } else if (rainfall > 30) {
        flood += 10 + (rainfall - 30) * 0.4
        sanit += 3
    }
    // Very low rainfall → water shortage signal
    if (rainfall < 20) {
        water += 8 + (20 - rainfall) * 0.4
    }

    // ── Temperature → primarily WATER SHORTAGE (evaporation/demand) ──
    if (temperature > 100) {
        water += 15                                    // Extreme heat → evaporation, demand surge
        power += 8                                     // Grid stress from cooling demand
        sanit += 5
    } else if (temperature > 85) {
        water += 5 + (temperature - 85) * 0.4
        power += 3
    }

    // ── Pump failure → primarily WATER SHORTAGE ──
    if (pumpFailure) {
        water += 25                                    // Direct water supply disruption
        sanit += 8                                     // Sanitation depends on water pressure
        // Hospitals are more vulnerable to pump failure
        if (f.facility_type !== 'School') {
            water += 8
            sanit += 5
        }
    }

    // ── Electricity failure → primarily POWER OUTAGE ──
    if (electricityFailure) {
        power += 45                                    // Direct massive power outage
        water += 8                                     // Electric pumps go offline
        sanit += 5
        // Hospitals critically depend on power (life support, cold storage)
        if (f.facility_type !== 'School') {
            power += 15
            sanit += 5
        } else {
            // Schools: less critical but still affected
            power += 5
        }
    }

    // ── Compound effects (smaller, targeted) ──
    if (pumpFailure && electricityFailure) {
        water += 10                                    // Double infra failure compounds water crisis
        sanit += 8
    }
    if (rainfall > 70 && electricityFailure) {
        power += 10                                    // Flooding damages electrical infra
        flood += 5
    }
    if (rainfall > 70 && pumpFailure) {
        flood += 5                                     // Pumps can't drain floodwater
    }
    if (temperature > 90 && pumpFailure) {
        water += 8                                     // Heat + no pump = critical water stress
    }

    // ── Factor in facility resilience (CRS) — resilient facilities absorb shocks ──
    const resilience = f.crs || 0.5                    // 0-1, higher = more resilient
    const baseW = (f.water_shortage_risk_prob || 0) * 100
    const baseF = (f.flood_risk_prob || 0) * 100
    const baseP = (f.power_outage_risk_prob || 0) * 100
    const baseS = (f.sanitation_failure_risk_prob || 0) * 100

    // Resilient facilities dampen scenario shocks more (multiplier 0.7–1.0)
    const shockMultiplier = 1.05 - resilience * 0.35
    water = baseW + (water - baseW) * shockMultiplier
    flood = baseF + (flood - baseF) * shockMultiplier
    power = baseP + (power - baseP) * shockMultiplier
    sanit = baseS + (sanit - baseS) * shockMultiplier

    // Clamp
    water = Math.min(100, Math.max(0, Math.round(water)))
    flood = Math.min(100, Math.max(0, Math.round(flood)))
    power = Math.min(100, Math.max(0, Math.round(power)))
    sanit = Math.min(100, Math.max(0, Math.round(sanit)))

    const risks = [
        { label: 'Water Shortage', v: water },
        { label: 'Flood', v: flood },
        { label: 'Power Outage', v: power },
        { label: 'Sanitation Failure', v: sanit },
    ]
    risks.sort((a, b) => b.v - a.v)

    return {
        name: f.facility_name,
        type: f.facility_type,
        district: f.district,
        waterShortage: water,
        floodRisk: flood,
        powerOutage: power,
        sanitationFail: sanit,
        topRisk: risks[0].label,
        topRiskPct: risks[0].v,
    }
}

// ── Risk colour helper ────────────────────────────────────────────────────────
function riskBadge(pct: number) {
    if (pct >= 70) return 'text-red-600 bg-red-50'
    if (pct >= 40) return 'text-orange-600 bg-orange-50'
    return 'text-green-600 bg-green-50'
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function Simulator() {
    const [facilities, setFacilities] = useState<Facility[]>([])
    const [loading, setLoading] = useState(true)
    const [searchTerm, setSearchTerm] = useState('')
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

    // Scenario inputs
    const [rainfall, setRainfall] = useState(0)
    const [temperature, setTemperature] = useState(55)
    const [pumpFailure, setPumpFailure] = useState(false)
    const [electricityFailure, setElectricityFailure] = useState(false)

    useEffect(() => {
        facilityService.getAll().then(data => { setFacilities(data); setLoading(false) })
    }, [])

    const filteredFacilities = useMemo(() => {
        if (!searchTerm) return facilities
        const q = searchTerm.toLowerCase()
        return facilities.filter(f =>
            f.facility_name.toLowerCase().includes(q) ||
            f.district.toLowerCase().includes(q) ||
            f.facility_type.toLowerCase().includes(q)
        )
    }, [facilities, searchTerm])

    const toggleFacility = (id: string) => {
        setSelectedIds(prev => {
            const next = new Set(prev)
            if (next.has(id)) next.delete(id); else next.add(id)
            return next
        })
    }
    const selectAll = () => setSelectedIds(new Set(filteredFacilities.map(f => f.facility_id)))
    const clearAll = () => setSelectedIds(new Set())

    // ── Simulation results ────────────────────────────────────────────────────
    const { scenarioDesc, simResults, peakProb, recommendedAction } = useMemo(() => {
        const parts: string[] = []
        if (rainfall > 70) parts.push('Heavy rainfall')
        else if (rainfall > 30) parts.push('Moderate rainfall')
        if (temperature > 100) parts.push('Extreme heat')
        else if (temperature > 85) parts.push('High heat')
        if (pumpFailure) parts.push('pump failure')
        if (electricityFailure) parts.push('electricity failure')
        if (parts.length === 0) parts.push('Normal conditions')
        const scenarioDesc = parts.join(' + ')

        const chosen = facilities.filter(f => selectedIds.has(f.facility_id))
        if (chosen.length === 0) {
            return {
                scenarioDesc,
                simResults: [] as SimResult[],
                peakProb: 0,
                recommendedAction: 'Select facilities on the left to begin simulation.',
            }
        }

        const simResults = chosen.map(f => simulateFacility(f, rainfall, temperature, pumpFailure, electricityFailure))
        simResults.sort((a, b) => b.topRiskPct - a.topRiskPct)
        const peakProb = simResults[0]?.topRiskPct ?? 0

        const action =
            peakProb >= 75 ? 'CRITICAL: Deploy emergency response teams, activate backup systems, and begin evacuation protocols for high-risk facilities.'
                : peakProb >= 50 ? 'WARNING: Prepare backup generators and water supplies. Alert facility managers and monitor conditions continuously.'
                    : peakProb >= 30 ? 'ADVISORY: Increase monitoring frequency. Ensure all backup systems are operational and staff are on standby.'
                        : 'Standard operating procedures. Continue routine monitoring.'

        return { scenarioDesc, simResults, peakProb, recommendedAction: action }
    }, [rainfall, temperature, pumpFailure, electricityFailure, facilities, selectedIds])

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[60vh]">
                <div className="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
        )
    }

    return (
        <div className="max-w-7xl mx-auto space-y-5">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-surface-800 flex items-center gap-2">
                    <Activity className="w-6 h-6 text-primary-500" />
                    Digital Twin Climate Simulator
                </h1>
                <p className="text-sm text-surface-500 mt-1">
                    Select facilities, adjust environmental parameters, and observe predicted impacts in real time.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">

                {/* ── Left: Facility Picker ─────────────────────────── */}
                <div className="lg:col-span-3 flex flex-col gap-3">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input type="text" placeholder="Search facilities…" value={searchTerm}
                            onChange={e => setSearchTerm(e.target.value)}
                            className="w-full pl-9 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-sm" />
                    </div>
                    <div className="flex gap-2">
                        <button onClick={selectAll} className="flex-1 text-xs font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg py-1.5 transition">
                            Select All ({filteredFacilities.length})
                        </button>
                        <button onClick={clearAll} className="flex-1 text-xs font-semibold text-slate-500 bg-slate-50 hover:bg-slate-100 rounded-lg py-1.5 transition">
                            Clear
                        </button>
                    </div>
                    <div className="bg-white border border-slate-200/60 rounded-xl shadow-sm overflow-hidden flex flex-col" style={{ height: '520px' }}>
                        <div className="px-4 py-2.5 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
                            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Facilities</span>
                            <span className="text-[11px] font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">{selectedIds.size} selected</span>
                        </div>
                        <div className="flex-1 overflow-y-auto divide-y divide-slate-50">
                            {filteredFacilities.length === 0 ? (
                                <p className="text-sm text-center py-8 text-slate-400">No facilities found.</p>
                            ) : filteredFacilities.map(f => {
                                const sel = selectedIds.has(f.facility_id)
                                const rc = f.risk_level === 'High' ? 'text-red-500 bg-red-50' : f.risk_level === 'Medium' ? 'text-orange-500 bg-orange-50' : 'text-green-500 bg-green-50'
                                return (
                                    <button key={f.facility_id} onClick={() => toggleFacility(f.facility_id)}
                                        className={`w-full text-left px-3 py-2.5 flex items-start gap-2.5 transition-colors ${sel ? 'bg-blue-50/60' : 'hover:bg-slate-50'}`}>
                                        <div className={`mt-0.5 w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 transition-colors ${sel ? 'bg-blue-500 border-blue-500' : 'border-slate-300'}`}>
                                            {sel && <Check className="w-3 h-3 text-white" />}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className={`text-sm font-semibold truncate ${sel ? 'text-blue-900' : 'text-slate-700'}`}>{f.facility_name}</p>
                                            <div className="flex items-center gap-2 mt-0.5 text-[11px] text-slate-400">
                                                <span className="flex items-center gap-0.5"><Building2 className="w-3 h-3" />{f.facility_type}</span>
                                                <span className="flex items-center gap-0.5"><MapPin className="w-3 h-3" />{f.district}</span>
                                            </div>
                                        </div>
                                        <span className={`mt-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded-md uppercase ${rc}`}>{f.risk_level}</span>
                                    </button>
                                )
                            })}
                        </div>
                    </div>
                </div>

                {/* ── Center: Scenario Controls ─────────────────────── */}
                <div className="lg:col-span-4">
                    <div className="bg-gradient-to-br from-blue-50 to-cyan-50 border border-blue-100/50 rounded-2xl p-6 shadow-sm h-full flex flex-col">
                        <h3 className="text-lg font-bold text-slate-800 mb-5">Scenario Parameters</h3>

                        {/* Rainfall */}
                        <div className="space-y-2 mb-6">
                            <label className="flex items-center justify-between text-sm font-semibold text-slate-700">
                                <span className="flex items-center gap-1.5"><CloudRain className="w-4 h-4 text-blue-500" />Rainfall Forecast</span>
                                <span className="text-blue-600 font-bold">{rainfall}%</span>
                            </label>
                            <input type="range" min="0" max="100" value={rainfall}
                                onChange={e => setRainfall(Number(e.target.value))}
                                className="w-full h-2 bg-blue-200 rounded-lg appearance-none cursor-pointer accent-blue-500" />
                            <div className="flex justify-between text-[10px] text-slate-400 font-medium"><span>0</span><span>100</span></div>
                        </div>

                        {/* Temperature */}
                        <div className="space-y-2 mb-6">
                            <label className="flex items-center justify-between text-sm font-semibold text-slate-700">
                                <span className="flex items-center gap-1.5"><Thermometer className="w-4 h-4 text-orange-500" />Temperature Increase</span>
                                <span className="text-blue-600 font-bold">{temperature}°F</span>
                            </label>
                            <input type="range" min="55" max="120" value={temperature}
                                onChange={e => setTemperature(Number(e.target.value))}
                                className="w-full h-2 bg-blue-200 rounded-lg appearance-none cursor-pointer accent-blue-500" />
                            <div className="flex justify-between text-[10px] text-slate-400 font-medium"><span>55</span><span>120</span></div>
                        </div>

                        {/* Toggles row */}
                        <div className="grid grid-cols-2 gap-4 mb-6">
                            {/* Pump Failure */}
                            <div className="bg-white/60 rounded-xl p-3 border border-blue-100/40">
                                <label className="text-xs font-semibold text-slate-600 flex items-center gap-1 mb-2">
                                    <Droplets className="w-3.5 h-3.5 text-cyan-500" />Pump Failure
                                </label>
                                <button onClick={() => setPumpFailure(!pumpFailure)}
                                    className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors duration-200 focus:outline-none ${pumpFailure ? 'bg-cyan-500' : 'bg-slate-200'}`}>
                                    <span className={`inline-block h-5 w-5 rounded-full bg-white shadow-sm transition duration-200 ${pumpFailure ? 'translate-x-8' : 'translate-x-1'}`} />
                                </button>
                            </div>
                            {/* Electricity Failure */}
                            <div className="bg-white/60 rounded-xl p-3 border border-blue-100/40">
                                <label className="text-xs font-semibold text-slate-600 flex items-center gap-1 mb-2">
                                    <Zap className="w-3.5 h-3.5 text-amber-500" />Electricity Failure
                                </label>
                                <button onClick={() => setElectricityFailure(!electricityFailure)}
                                    className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors duration-200 focus:outline-none ${electricityFailure ? 'bg-amber-500' : 'bg-slate-200'}`}>
                                    <span className={`inline-block h-5 w-5 rounded-full bg-white shadow-sm transition duration-200 ${electricityFailure ? 'translate-x-8' : 'translate-x-1'}`} />
                                </button>
                            </div>
                        </div>

                        {/* Active scenario badge */}
                        <div className="mt-auto pt-4 border-t border-blue-100/60">
                            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">Active Scenario</p>
                            <p className="text-sm font-bold text-slate-800">{scenarioDesc}</p>
                        </div>
                    </div>
                </div>

                {/* ── Right: Live Scenario Output ──────────────────── */}
                <div className="lg:col-span-5 flex flex-col gap-4">
                    {/* Peak probability hero */}
                    <div className="bg-white border border-slate-200/60 rounded-2xl p-5 shadow-sm">
                        <div className="flex items-center justify-between mb-1">
                            <h3 className="text-lg font-bold text-slate-800">Live Scenario Output</h3>
                            <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full ring-1 ring-blue-200/50">
                                {selectedIds.size} facilities
                            </span>
                        </div>
                        <p className="text-xs text-slate-400 mb-3">Peak risk probability across selected facilities</p>
                        <div className="flex items-end justify-between">
                            <span className={`text-5xl font-light tracking-tight ${peakProb >= 70 ? 'text-red-500' : peakProb >= 40 ? 'text-orange-500' : 'text-green-500'}`}>
                                {peakProb}%
                            </span>
                            <span className={`text-sm font-bold px-3 py-1 rounded-full ${peakProb >= 70 ? 'bg-red-50 text-red-600' : peakProb >= 40 ? 'bg-orange-50 text-orange-600' : 'bg-green-50 text-green-600'}`}>
                                {peakProb >= 70 ? 'Critical' : peakProb >= 40 ? 'Warning' : 'Normal'}
                            </span>
                        </div>
                    </div>

                    {/* Per-facility results table */}
                    <div className="bg-white border border-slate-200/60 rounded-2xl shadow-sm overflow-hidden flex-1" style={{ minHeight: '200px' }}>
                        <div className="px-5 py-2.5 border-b border-slate-100 bg-slate-50 flex items-center gap-1.5">
                            <MapPin className="w-3.5 h-3.5 text-slate-500" />
                            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Per-Facility Impact</span>
                        </div>
                        <div className="overflow-y-auto" style={{ maxHeight: '240px' }}>
                            {simResults.length === 0 ? (
                                <p className="text-sm text-slate-400 text-center py-8">
                                    {selectedIds.size === 0 ? 'Select facilities to simulate.' : 'Adjust parameters to see impacts.'}
                                </p>
                            ) : (
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="text-[10px] text-slate-400 uppercase tracking-wider border-b border-slate-50">
                                            <th className="text-left px-4 py-2 font-semibold">Facility</th>
                                            <th className="text-center px-1 py-2 font-semibold"><Droplets className="w-3 h-3 mx-auto" title="Water" /></th>
                                            <th className="text-center px-1 py-2 font-semibold"><Waves className="w-3 h-3 mx-auto" title="Flood" /></th>
                                            <th className="text-center px-1 py-2 font-semibold"><Zap className="w-3 h-3 mx-auto" title="Power" /></th>
                                            <th className="text-center px-1 py-2 font-semibold"><ShieldAlert className="w-3 h-3 mx-auto" title="Sanitation" /></th>
                                            <th className="text-right px-4 py-2 font-semibold">Top Risk</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-50">
                                        {simResults.map(r => (
                                            <tr key={r.name} className="hover:bg-slate-50/50 transition">
                                                <td className="px-4 py-2 max-w-[140px]">
                                                    <p className="font-medium text-slate-700 truncate text-xs">{r.name}</p>
                                                    <p className="text-[10px] text-slate-400">{r.type} · {r.district}</p>
                                                </td>
                                                <td className="text-center px-1 py-2"><span className={`text-[11px] font-bold px-1.5 py-0.5 rounded ${riskBadge(r.waterShortage)}`}>{r.waterShortage}%</span></td>
                                                <td className="text-center px-1 py-2"><span className={`text-[11px] font-bold px-1.5 py-0.5 rounded ${riskBadge(r.floodRisk)}`}>{r.floodRisk}%</span></td>
                                                <td className="text-center px-1 py-2"><span className={`text-[11px] font-bold px-1.5 py-0.5 rounded ${riskBadge(r.powerOutage)}`}>{r.powerOutage}%</span></td>
                                                <td className="text-center px-1 py-2"><span className={`text-[11px] font-bold px-1.5 py-0.5 rounded ${riskBadge(r.sanitationFail)}`}>{r.sanitationFail}%</span></td>
                                                <td className="text-right px-4 py-2">
                                                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${riskBadge(r.topRiskPct)}`}>
                                                        {r.topRisk}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    </div>

                    {/* Recommended Action */}
                    <div className={`rounded-2xl p-4 shadow-sm border ${peakProb >= 70 ? 'bg-red-50 border-red-200/60' : peakProb >= 40 ? 'bg-orange-50 border-orange-200/60' : 'bg-white border-slate-200/60'}`}>
                        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                            <AlertCircle className="w-3.5 h-3.5" />
                            Recommended Action
                        </h4>
                        <p className={`text-sm font-medium leading-relaxed ${peakProb >= 70 ? 'text-red-800' : peakProb >= 40 ? 'text-orange-800' : 'text-slate-800'}`}>
                            {recommendedAction}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
