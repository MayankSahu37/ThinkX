import { useEffect, useState, useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import { Link } from 'react-router-dom'
import { facilityService } from '../services/api'
import type { Facility } from '../utils/types'
import { Map as MapIcon, Layers, AlertTriangle } from 'lucide-react'

function createIcon(riskLevel: string) {
    const colors: Record<string, string> = {
        High: '#ef4444',
        Medium: '#f97316',
        Low: '#22c55e',
    }
    const color = colors[riskLevel] || '#64748b'

    return L.divIcon({
        className: '',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
        popupAnchor: [0, -16],
        html: `<div style="
      width:28px;height:28px;border-radius:50%;
      background:${color};border:3px solid white;
      box-shadow:0 2px 8px rgba(0,0,0,0.3);
      display:flex;align-items:center;justify-content:center;
    ">
      <div style="width:8px;height:8px;border-radius:50%;background:white;opacity:0.8;"></div>
    </div>`,
    })
}

function MapBounds({ facilities }: { facilities: Facility[] }) {
    const map = useMap()
    useEffect(() => {
        if (facilities.length > 0) {
            const bounds = L.latLngBounds(facilities.map(f => [f.latitude, f.longitude]))
            map.fitBounds(bounds, { padding: [50, 50] })
        }
    }, [facilities, map])
    return null
}

export default function RiskMap() {
    const [facilities, setFacilities] = useState<Facility[]>([])
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState<string>('All')

    useEffect(() => {
        facilityService.getAll().then(data => {
            setFacilities(data)
            setLoading(false)
        })
    }, [])

    const filtered = useMemo(() => {
        if (filter === 'All') return facilities
        return facilities.filter(f => f.risk_level === filter)
    }, [facilities, filter])

    const counts = useMemo(() => ({
        All: facilities.length,
        High: facilities.filter(f => f.risk_level === 'High').length,
        Medium: facilities.filter(f => f.risk_level === 'Medium').length,
        Low: facilities.filter(f => f.risk_level === 'Low').length,
    }), [facilities])

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="w-8 h-8 border-3 border-primary-500 border-t-transparent rounded-full animate-spin" />
            </div>
        )
    }

    return (
        <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div>
                    <h1 className="text-2xl font-bold text-surface-900 flex items-center gap-2">
                        <MapIcon className="w-6 h-6 text-primary-500" /> Facility Risk Map
                    </h1>
                    <p className="text-sm text-surface-500 mt-1">Interactive map showing facility risk levels across Raipur District</p>
                </div>
                <div className="flex items-center gap-2">
                    {(['All', 'High', 'Medium', 'Low'] as const).map(level => {
                        const colors: Record<string, string> = { All: 'bg-surface-600', High: 'bg-risk-high', Medium: 'bg-risk-medium', Low: 'bg-risk-low' }
                        return (
                            <button
                                key={level}
                                onClick={() => setFilter(level)}
                                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all duration-200
                  ${filter === level
                                        ? `text-white ${colors[level]} shadow-md`
                                        : 'text-surface-600 bg-white border border-surface-200 hover:border-surface-300'
                                    }`}
                            >
                                {level}
                                <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${filter === level ? 'bg-white/20' : 'bg-surface-100'}`}>
                                    {counts[level]}
                                </span>
                            </button>
                        )
                    })}
                </div>
            </div>

            {/* Legend */}
            <div className="flex items-center gap-5 px-4 py-2.5 bg-white rounded-xl border border-surface-200/60 shadow-sm">
                <Layers className="w-4 h-4 text-surface-400" />
                <div className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-full bg-risk-high" />
                    <span className="text-xs text-surface-600">High Risk</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-full bg-risk-medium" />
                    <span className="text-xs text-surface-600">Medium Risk</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-full bg-risk-low" />
                    <span className="text-xs text-surface-600">Low Risk</span>
                </div>
            </div>

            {/* Map */}
            <div className="rounded-2xl overflow-hidden border border-surface-200/60 shadow-sm" style={{ height: 'calc(100vh - 280px)', minHeight: '400px' }}>
                <MapContainer
                    center={[21.25, 81.63]}
                    zoom={10}
                    className="h-full w-full"
                    zoomControl={true}
                >
                    <TileLayer
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    <MapBounds facilities={filtered} />
                    {filtered.map(f => (
                        <Marker key={f.facility_id} position={[f.latitude, f.longitude]} icon={createIcon(f.risk_level)}>
                            <Popup>
                                <div className="min-w-[200px] p-1">
                                    <h3 className="text-sm font-bold text-surface-900 mb-1">{f.facility_name}</h3>
                                    <div className="space-y-1.5 text-xs text-surface-600">
                                        <div className="flex justify-between">
                                            <span>Type:</span>
                                            <span className="font-medium text-surface-800">{f.facility_type}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span>Risk Level:</span>
                                            <span className={`font-semibold ${f.risk_level === 'High' ? 'text-red-600' : f.risk_level === 'Medium' ? 'text-orange-600' : 'text-green-600'}`}>
                                                {f.risk_level}
                                            </span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span>CRS:</span>
                                            <span className="font-medium text-surface-800">{Math.round(f.crs * 100)}%</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span>Top Risk:</span>
                                            <span className="font-medium text-surface-800 capitalize">{f.top_risk_type?.replace(/_/g, ' ') || 'N/A'}</span>
                                        </div>
                                        {f.alert_flag && (
                                            <div className="pt-1.5 border-t border-surface-200">
                                                <p className="font-semibold text-surface-700 mb-1 flex items-center gap-1">
                                                    <AlertTriangle className="w-3 h-3 text-amber-500" /> Alert: {f.alert_level}
                                                </p>
                                            </div>
                                        )}
                                        <Link
                                            to={`/facilities/${encodeURIComponent(f.facility_id)}`}
                                            className="block mt-2 text-center py-1.5 px-3 bg-primary-50 text-primary-700 font-semibold rounded-lg hover:bg-primary-100 transition text-xs"
                                        >
                                            View Details →
                                        </Link>
                                    </div>
                                </div>
                            </Popup>
                        </Marker>
                    ))}
                </MapContainer>
            </div>
        </div>
    )
}
