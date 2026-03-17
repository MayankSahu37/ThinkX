import { useState, useEffect } from 'react'
import { Search, MapPin, Building2, AlertTriangle } from 'lucide-react'
import { facilityService } from '../services/api'
import type { Facility } from '../utils/types'
import XAIPanel from '../components/XAIPanel'

export default function XAIAnalysis() {
    const [facilities, setFacilities] = useState<Facility[]>([])
    const [searchTerm, setSearchTerm] = useState('')
    const [selectedId, setSelectedId] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        facilityService.getAll().then(data => {
            setFacilities(data)
            // Pre-select the highest risk facility
            if (data.length > 0) {
                const highestRisk = [...data].sort((a, b) => b.top_risk_score - a.top_risk_score)[0]
                setSelectedId(highestRisk.facility_id)
            }
            setLoading(false)
        })
    }, [])

    const filtered = facilities.filter(f =>
        f.facility_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        f.district.toLowerCase().includes(searchTerm.toLowerCase())
    )

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[60vh]">
                <div className="w-8 h-8 border-3 border-violet-500 border-t-transparent rounded-full animate-spin" />
            </div>
        )
    }

    return (
        <div className="max-w-5xl mx-auto space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-slate-800">Explainable AI (XAI) Analysis</h1>
                <p className="text-sm text-slate-500 mt-1">
                    Understand the active risk drivers behind ClimaSafe's predictions.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left col: Search & List */}
                <div className="lg:col-span-4 flex flex-col gap-4">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search facility or district..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-9 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-violet-500 transition-shadow shadow-sm"
                        />
                    </div>

                    <div className="bg-white border border-slate-200/60 rounded-xl shadow-sm overflow-hidden flex flex-col h-[600px]">
                        <div className="px-4 py-3 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
                            <span className="text-xs font-semibold text-slate-600 uppercase">Facilities</span>
                            <span className="text-xs font-medium text-slate-400 bg-slate-200 px-2 py-0.5 rounded-full">{filtered.length}</span>
                        </div>
                        <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
                            {filtered.length === 0 ? (
                                <p className="text-sm text-center py-6 text-slate-500">No facilities found.</p>
                            ) : (
                                filtered.map(f => {
                                    const isSelected = selectedId === f.facility_id
                                    const riskColor = f.risk_level === 'High' ? 'text-red-500' : f.risk_level === 'Medium' ? 'text-orange-500' : 'text-green-500'
                                    const riskBg = f.risk_level === 'High' ? 'bg-red-50' : f.risk_level === 'Medium' ? 'bg-orange-50' : 'bg-green-50'

                                    return (
                                        <button
                                            key={f.facility_id}
                                            onClick={() => setSelectedId(f.facility_id)}
                                            className={`w-full text-left p-3 rounded-lg transition-all border ${isSelected
                                                    ? 'bg-violet-50 border-violet-200 shadow-sm'
                                                    : 'bg-transparent border-transparent hover:bg-slate-50 cursor-pointer'
                                                }`}
                                        >
                                            <div className="flex justify-between items-start mb-1">
                                                <p className={`text-sm font-semibold truncate pr-2 ${isSelected ? 'text-violet-900' : 'text-slate-700'}`}>
                                                    {f.facility_name}
                                                </p>
                                                <div className={`shrink-0 flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${riskBg} ${riskColor}`}>
                                                    {f.risk_level}
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3 text-xs text-slate-500">
                                                <span className="flex items-center gap-1">
                                                    <Building2 className="w-3 h-3" />
                                                    {f.facility_type}
                                                </span>
                                                <span className="flex items-center gap-1">
                                                    <MapPin className="w-3 h-3" />
                                                    {f.district}
                                                </span>
                                            </div>
                                        </button>
                                    )
                                })
                            )}
                        </div>
                    </div>
                </div>

                {/* Right col: XAI Panel */}
                <div className="lg:col-span-8 flex flex-col gap-4">
                    {/* Explainer banner */}
                    <div className="p-4 rounded-xl bg-gradient-to-br from-violet-600 to-violet-800 text-white shadow-md flex items-start gap-4">
                        <div className="p-2.5 bg-white/10 rounded-xl backdrop-blur-sm shrink-0">
                            <AlertTriangle className="w-6 h-6 text-violet-100" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-white">How to read this analysis</h3>
                            <p className="text-sm text-violet-100 mt-1 leading-relaxed">
                                The XAI engine breaks down the predicted risk into specific contributing factors.
                                The factors with the highest contribution percentages are the primary drivers of the facility's vulnerability.
                            </p>
                        </div>
                    </div>

                    {/* Dynamic panel instance */}
                    {selectedId ? (
                        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <XAIPanel facilityId={selectedId} />
                        </div>
                    ) : (
                        <div className="flex items-center justify-center h-64 bg-slate-50 border border-dashed border-slate-300 rounded-2xl text-slate-400 text-sm">
                            Select a facility to view its AI explanation.
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
