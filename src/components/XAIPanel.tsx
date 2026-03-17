import { useEffect, useState, useRef } from 'react'
import {
    CloudRain, Waves, Droplets, Zap, TrendingUp, ShieldAlert,
    Sun, Brain, ChevronRight, Info,
} from 'lucide-react'
import { xaiService } from '../services/api'
import type { XAIExplanation, XAIFactor } from '../utils/types'

// ── Icon map ──────────────────────────────────────────────────────────────────
const ICON_MAP: Record<string, any> = {
    'cloud-rain': CloudRain,
    'waves': Waves,
    'droplets': Droplets,
    'zap': Zap,
    'trending-up': TrendingUp,
    'shield-alert': ShieldAlert,
    'sun': Sun,
}
const FactorIcon = ({ name, className, style }: { name: string; className?: string; style?: React.CSSProperties }) => {
    const Comp = ICON_MAP[name] || ShieldAlert
    return <Comp className={className} style={style} />
}

// ── Gauge SVG ─────────────────────────────────────────────────────────────────
function GaugeDial({ percent, color }: { percent: number; color: string }) {
    const radius = 70
    const stroke = 10
    const svgSize = (radius + stroke) * 2
    const cx = svgSize / 2
    const cy = svgSize / 2

    // The arc spans 220° (from -200° to 40°) so needle at -200° = 0%, 40° = 100%
    const START_DEG = -200
    const SWEEP = 220
    const toRad = (d: number) => (d * Math.PI) / 180

    const pct = Math.min(100, Math.max(0, percent))
    const needleDeg = START_DEG + (pct / 100) * SWEEP
    const needleRad = toRad(needleDeg)
    const needleLen = radius - stroke - 6
    const nx = cx + needleLen * Math.cos(needleRad)
    const ny = cy + needleLen * Math.sin(needleRad)

    // Build track arc path
    const arcPath = (startDeg: number, endDeg: number) => {
        const s = toRad(startDeg)
        const e = toRad(endDeg)
        const x1 = cx + radius * Math.cos(s)
        const y1 = cy + radius * Math.sin(s)
        const x2 = cx + radius * Math.cos(e)
        const y2 = cy + radius * Math.sin(e)
        const large = endDeg - startDeg > 180 ? 1 : 0
        return `M ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2}`
    }

    // Colored segments: 0-33% green, 33-66% amber, 66-100% red
    const seg33Deg = START_DEG + 0.33 * SWEEP
    const seg66Deg = START_DEG + 0.66 * SWEEP
    const END_DEG = START_DEG + SWEEP

    return (
        <svg width={svgSize} height={svgSize * 0.7} viewBox={`0 0 ${svgSize} ${svgSize}`}
            style={{ overflow: 'visible' }}>
            {/* Track background */}
            <path d={arcPath(START_DEG, END_DEG)} fill="none" stroke="#e2e8f0" strokeWidth={stroke} strokeLinecap="round" />
            {/* Green segment */}
            <path d={arcPath(START_DEG, seg33Deg)} fill="none" stroke="#22c55e" strokeWidth={stroke} strokeLinecap="round" opacity={0.7} />
            {/* Amber segment */}
            <path d={arcPath(seg33Deg, seg66Deg)} fill="none" stroke="#f97316" strokeWidth={stroke} strokeLinecap="round" opacity={0.7} />
            {/* Red segment */}
            <path d={arcPath(seg66Deg, END_DEG)} fill="none" stroke="#ef4444" strokeWidth={stroke} strokeLinecap="round" opacity={0.7} />
            {/* Active fill up to needle */}
            <path d={arcPath(START_DEG, needleDeg)} fill="none" stroke={color} strokeWidth={stroke + 1} strokeLinecap="round" />
            {/* Needle */}
            <line x1={cx} y1={cy} x2={nx} y2={ny} stroke={color} strokeWidth={3} strokeLinecap="round" />
            <circle cx={cx} cy={cy} r={7} fill={color} />
            <circle cx={cx} cy={cy} r={3} fill="white" />
            {/* Labels */}
            <text x={cx - radius + 4} y={cy + 22} fill="#94a3b8" fontSize={10} textAnchor="middle">0</text>
            <text x={cx + radius - 4} y={cy + 22} fill="#94a3b8" fontSize={10} textAnchor="middle">100%</text>
        </svg>
    )
}

// ── Contribution Bar ──────────────────────────────────────────────────────────
function ContributionBar({ factor, animate, index }: { factor: XAIFactor; animate: boolean; index: number }) {
    const barRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        if (!animate || !barRef.current) return
        const el = barRef.current
        el.style.width = '0%'
        const timer = setTimeout(() => {
            el.style.transition = `width 0.8s cubic-bezier(0.34,1.56,0.64,1)`
            el.style.width = `${factor.contribution_pct}%`
        }, 100 + index * 120)
        return () => clearTimeout(timer)
    }, [animate, factor.contribution_pct, index])

    const severity =
        factor.contribution_pct >= 40 ? { bg: '#fef2f2', bar: '#ef4444', text: '#b91c1c', icon: '#dc2626' } :
            factor.contribution_pct >= 20 ? { bg: '#fff7ed', bar: '#f97316', text: '#c2410c', icon: '#ea580c' } :
                { bg: '#f0fdf4', bar: '#22c55e', text: '#166534', icon: '#16a34a' }

    return (
        <div className="flex items-start gap-3 p-3 rounded-xl transition-all hover:brightness-95"
            style={{ backgroundColor: severity.bg }}>
            <div className="flex items-center justify-center w-9 h-9 rounded-lg shrink-0"
                style={{ backgroundColor: `${severity.bar}18` }}>
                <FactorIcon name={factor.icon} className="w-4 h-4" style={{ color: severity.icon } as any} />
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1.5">
                    <p className="text-sm font-semibold leading-tight" style={{ color: severity.text }}>
                        {factor.factor}
                    </p>
                    <div className="flex items-center gap-2 shrink-0 ml-2">
                        <span className="text-[11px] font-medium px-1.5 py-0.5 rounded-md"
                            style={{ backgroundColor: `${severity.bar}20`, color: severity.text }}>
                            {factor.contribution_pct.toFixed(0)}%
                        </span>
                        <span className="text-[11px] text-slate-500 font-mono">{factor.raw_value}</span>
                    </div>
                </div>
                <div className="w-full h-2 rounded-full bg-white/60 overflow-hidden">
                    <div ref={barRef} className="h-full rounded-full" style={{ backgroundColor: severity.bar }} />
                </div>
            </div>
        </div>
    )
}

// ── Risk colour helper ────────────────────────────────────────────────────────
function riskColor(pct: number): string {
    if (pct >= 66) return '#ef4444'
    if (pct >= 33) return '#f97316'
    return '#22c55e'
}

// ── Main component ────────────────────────────────────────────────────────────
interface XAIPanelProps {
    facilityId: string
    /** If true, fetches its own data. Otherwise accepts pre-fetched data. */
    explanation?: XAIExplanation | null
}

export default function XAIPanel({ facilityId, explanation: extExplanation }: XAIPanelProps) {
    const [data, setData] = useState<XAIExplanation | null>(extExplanation ?? null)
    const [loading, setLoading] = useState(!extExplanation)
    const [animate, setAnimate] = useState(false)

    useEffect(() => {
        if (extExplanation !== undefined) {
            setData(extExplanation)
            setLoading(false)
            setAnimate(true)
            return
        }
        setLoading(true)
        xaiService.getExplanation(facilityId).then(d => {
            setData(d)
            setLoading(false)
            setTimeout(() => setAnimate(true), 50)
        })
    }, [facilityId, extExplanation])

    if (loading) {
        return (
            <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm">
                <div className="flex items-center gap-2 mb-5">
                    <Brain className="w-4 h-4 text-violet-500" />
                    <span className="text-sm font-semibold text-slate-700">AI Explanation</span>
                </div>
                <div className="space-y-3">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-14 bg-slate-100 rounded-xl animate-pulse" />
                    ))}
                </div>
            </div>
        )
    }

    if (!data) {
        return (
            <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm text-center">
                <Brain className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-500">XAI data not available for this facility.</p>
            </div>
        )
    }

    const riskPct = data.top_risk_score_pct
    const confPct = data.confidence_pct
    const color = riskColor(riskPct)
    const riskBg = riskPct >= 66 ? '#fef2f2' : riskPct >= 33 ? '#fff7ed' : '#f0fdf4'
    const riskBorder = riskPct >= 66 ? '#fca5a5' : riskPct >= 33 ? '#fed7aa' : '#bbf7d0'

    return (
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
            {/* Header */}
            <div className="px-5 pt-5 pb-0 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-violet-50">
                        <Brain className="w-4 h-4 text-violet-600" />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold text-slate-800">AI Explanation</h3>
                        <p className="text-[11px] text-slate-400">Why was this risk predicted?</p>
                    </div>
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-violet-50 border border-violet-100">
                    <span className="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse" />
                    <span className="text-[11px] font-semibold text-violet-700">XAI Active</span>
                </div>
            </div>

            {/* Gauge + Confidence */}
            <div className="flex flex-col sm:flex-row items-center gap-4 px-5 py-4">
                {/* Gauge */}
                <div className="flex flex-col items-center">
                    <GaugeDial percent={riskPct} color={color} />
                    <div className="mt-1 text-center">
                        <p className="text-3xl font-black" style={{ color }}>{riskPct.toFixed(0)}%</p>
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mt-0.5">{data.top_risk_label}</p>
                    </div>
                </div>

                {/* Stats */}
                <div className="flex-1 w-full space-y-3">
                    {/* Confidence */}
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                        <div className="flex items-center justify-between mb-1.5">
                            <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Model Confidence</span>
                            <span className="text-sm font-bold text-slate-800">{confPct.toFixed(0)}%</span>
                        </div>
                        <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                            <div className="h-full rounded-full bg-gradient-to-r from-violet-400 to-violet-600 transition-all duration-1000"
                                style={{ width: animate ? `${confPct}%` : '0%' }} />
                        </div>
                    </div>

                    {/* Risk badge */}
                    <div className="p-3 rounded-xl border" style={{ backgroundColor: riskBg, borderColor: riskBorder }}>
                        <p className="text-[11px] font-semibold uppercase tracking-wider mb-1" style={{ color }}>Predicted Risk</p>
                        <div className="flex items-center justify-between">
                            <p className="text-sm font-bold" style={{ color }}>{data.top_risk_label}</p>
                            <ChevronRight className="w-4 h-4" style={{ color }} />
                        </div>
                        <p className="text-[11px] text-slate-500 mt-1">
                            {data.facility_type} · {data.facility_name}
                        </p>
                    </div>

                    {/* Info note */}
                    <div className="flex items-start gap-2 text-[11px] text-slate-400 px-1">
                        <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                        <span>Contributions are derived from weighted environmental inputs and normalized across all facilities.</span>
                    </div>
                </div>
            </div>

            {/* Divider */}
            <div className="mx-5 border-t border-slate-100" />

            {/* Factor list */}
            <div className="px-5 py-4 space-y-2">
                <p className="text-xs font-bold text-slate-600 uppercase tracking-widest mb-3">
                    Top Contributing Factors
                </p>
                {data.explanations.map((f, i) => (
                    <ContributionBar key={f.key} factor={f} animate={animate} index={i} />
                ))}
            </div>
        </div>
    )
}
