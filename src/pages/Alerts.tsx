import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { alertService } from '../services/api'
import type { Alert } from '../utils/types'
import { AlertTriangle, Clock, ArrowUpRight, Bell, Shield } from 'lucide-react'

export default function Alerts() {
    const [alerts, setAlerts] = useState<Alert[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        alertService.getAll().then(data => { setAlerts(data); setLoading(false) })
    }, [])

    if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500 border-t-transparent rounded-full animate-spin" /></div>

    const criticalAlerts = alerts.filter(a => a.riskLevel === 'Critical')
    const highAlerts = alerts.filter(a => a.riskLevel === 'High')
    const otherAlerts = alerts.filter(a => a.riskLevel !== 'Critical' && a.riskLevel !== 'High')

    const formatTime = (ts: string) => {
        if (!ts) return 'N/A'
        const d = new Date(ts)
        if (isNaN(d.getTime())) return ts
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-surface-900 flex items-center gap-2">
                    <Bell className="w-6 h-6 text-primary-500" /> Alerts
                </h1>
                <p className="text-sm text-surface-500 mt-1">Facilities with high predicted climate risk requiring attention</p>
            </div>

            {/* Summary */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-red-50 border border-red-200/60 rounded-2xl p-4 flex items-center gap-4">
                    <div className="p-2.5 bg-red-100 rounded-xl"><AlertTriangle className="w-5 h-5 text-red-600" /></div>
                    <div><p className="text-2xl font-bold text-red-700">{criticalAlerts.length + highAlerts.length}</p><p className="text-xs text-red-600 font-medium">Critical / High Alerts</p></div>
                </div>
                <div className="bg-orange-50 border border-orange-200/60 rounded-2xl p-4 flex items-center gap-4">
                    <div className="p-2.5 bg-orange-100 rounded-xl"><Shield className="w-5 h-5 text-orange-600" /></div>
                    <div><p className="text-2xl font-bold text-orange-700">{otherAlerts.length}</p><p className="text-xs text-orange-600 font-medium">Advisory Alerts</p></div>
                </div>
                <div className="bg-primary-50 border border-primary-200/60 rounded-2xl p-4 flex items-center gap-4">
                    <div className="p-2.5 bg-primary-100 rounded-xl"><Clock className="w-5 h-5 text-primary-600" /></div>
                    <div><p className="text-2xl font-bold text-primary-700">{alerts.length}</p><p className="text-xs text-primary-600 font-medium">Total Active</p></div>
                </div>
            </div>

            {/* Alerts Table */}
            <div className="bg-white rounded-2xl border border-surface-200/60 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-surface-100">
                    <h3 className="text-sm font-semibold text-surface-700">Active Alerts</h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-surface-50/50">
                                <th className="px-5 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Facility</th>
                                <th className="px-5 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Risk Level</th>
                                <th className="px-5 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Top Risk</th>
                                <th className="px-5 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Predicted Issue</th>
                                <th className="px-5 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Recommended Action</th>
                                <th className="px-5 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Updated</th>
                                <th className="px-5 py-3 text-right text-xs font-semibold text-surface-500 uppercase tracking-wider">Details</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-surface-100">
                            {alerts.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="px-5 py-12 text-center text-surface-400">
                                        No active alerts — all facilities are within normal parameters
                                    </td>
                                </tr>
                            ) : (
                                alerts.map(a => (
                                    <tr key={a.id} className="hover:bg-surface-50/50 transition">
                                        <td className="px-5 py-3.5">
                                            <div>
                                                <p className="font-medium text-surface-800">{a.facilityName}</p>
                                                <p className="text-xs text-surface-400">{a.facilityType}</p>
                                            </div>
                                        </td>
                                        <td className="px-5 py-3.5">
                                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${a.riskLevel === 'Critical' ? 'bg-red-100 text-red-800 border border-red-300' :
                                                a.riskLevel === 'High' ? 'bg-red-50 text-red-700 border border-red-200' :
                                                    a.riskLevel === 'Medium' ? 'bg-orange-50 text-orange-700 border border-orange-200' :
                                                        'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                                }`}>
                                                <span className={`w-1.5 h-1.5 rounded-full ${a.riskLevel === 'Critical' ? 'bg-red-600 animate-pulse' : a.riskLevel === 'High' ? 'bg-red-500' : a.riskLevel === 'Medium' ? 'bg-orange-500' : 'bg-emerald-500'}`} />
                                                {a.riskLevel}
                                            </span>
                                        </td>
                                        <td className="px-5 py-3.5">
                                            <span className="text-xs font-medium text-surface-700 capitalize">{a.topRiskType?.replace(/_/g, ' ')}</span>
                                        </td>
                                        <td className="px-5 py-3.5 text-surface-700 max-w-[220px]">{a.predictedIssue}</td>
                                        <td className="px-5 py-3.5 text-surface-600 max-w-[220px]">{a.recommendedAction}</td>
                                        <td className="px-5 py-3.5 text-surface-500 whitespace-nowrap">
                                            <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{formatTime(a.timestamp)}</span>
                                        </td>
                                        <td className="px-5 py-3.5 text-right">
                                            <Link to={`/facilities/${encodeURIComponent(a.facilityId)}`} className="inline-flex items-center gap-1 text-xs font-semibold text-primary-600 hover:text-primary-700 transition">
                                                View <ArrowUpRight className="w-3.5 h-3.5" />
                                            </Link>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}
