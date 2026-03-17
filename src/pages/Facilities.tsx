import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { facilityService } from '../services/api'
import type { Facility } from '../utils/types'
import { Search, Filter, ChevronLeft, ChevronRight, Building2, ArrowUpDown } from 'lucide-react'

const PAGE_SIZE = 8

export default function Facilities() {
    const [facilities, setFacilities] = useState<Facility[]>([])
    const [loading, setLoading] = useState(true)
    const [search, setSearch] = useState('')
    const [riskFilter, setRiskFilter] = useState<string>('All')
    const [page, setPage] = useState(1)
    const [sortField, setSortField] = useState<'crs' | 'name'>('crs')
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

    useEffect(() => {
        facilityService.getAll().then(data => {
            setFacilities(data)
            setLoading(false)
        })
    }, [])

    const filtered = useMemo(() => {
        let data = [...facilities]

        if (search) {
            const q = search.toLowerCase()
            data = data.filter(f =>
                f.facility_name.toLowerCase().includes(q) ||
                f.district.toLowerCase().includes(q) ||
                f.facility_type.toLowerCase().includes(q)
            )
        }

        if (riskFilter !== 'All') {
            data = data.filter(f => f.risk_level === riskFilter)
        }

        data.sort((a, b) => {
            const mul = sortDir === 'asc' ? 1 : -1
            if (sortField === 'crs') return (a.crs - b.crs) * mul
            return a.facility_name.localeCompare(b.facility_name) * mul
        })

        return data
    }, [facilities, search, riskFilter, sortField, sortDir])

    const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
    const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

    useEffect(() => { setPage(1) }, [search, riskFilter])

    const toggleSort = (field: 'crs' | 'name') => {
        if (sortField === field) {
            setSortDir(d => d === 'asc' ? 'desc' : 'asc')
        } else {
            setSortField(field)
            setSortDir('desc')
        }
    }

    const riskBadge = (level: string) => {
        const styles: Record<string, string> = {
            High: 'bg-red-50 text-red-700 border-red-200',
            Medium: 'bg-orange-50 text-orange-700 border-orange-200',
            Low: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        }
        const dot: Record<string, string> = { High: 'bg-red-500', Medium: 'bg-orange-500', Low: 'bg-emerald-500' }
        return (
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${styles[level] || ''}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${dot[level] || ''}`} />
                {level}
            </span>
        )
    }

    const statusFromAlert = (f: Facility) => {
        if (f.alert_level === 'Critical') return 'Action Required'
        if (f.alert_level === 'High' || f.alert_flag) return 'Under Review'
        return 'Active'
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="w-8 h-8 border-3 border-primary-500 border-t-transparent rounded-full animate-spin" />
            </div>
        )
    }

    return (
        <div className="space-y-4">
            <div>
                <h1 className="text-2xl font-bold text-surface-900 flex items-center gap-2">
                    <Building2 className="w-6 h-6 text-primary-500" /> Facilities
                </h1>
                <p className="text-sm text-surface-500 mt-1">Comprehensive list of monitored facilities in Raipur District</p>
            </div>

            {/* Toolbar */}
            <div className="flex flex-col sm:flex-row gap-3">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
                    <input
                        type="text"
                        placeholder="Search by name, district, or type..."
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-surface-200 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 transition"
                    />
                </div>
                <div className="flex items-center gap-2">
                    <Filter className="w-4 h-4 text-surface-400" />
                    {(['All', 'High', 'Medium', 'Low'] as const).map(level => {
                        const active = riskFilter === level
                        return (
                            <button
                                key={level}
                                onClick={() => setRiskFilter(level)}
                                className={`px-3 py-2 rounded-xl text-xs font-semibold transition-all duration-200 ${active
                                    ? 'bg-primary-600 text-white shadow-md'
                                    : 'bg-white text-surface-600 border border-surface-200 hover:border-surface-300'
                                    }`}
                            >
                                {level}
                            </button>
                        )
                    })}
                </div>
            </div>

            {/* Table */}
            <div className="bg-white rounded-2xl border border-surface-200/60 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-surface-50/50">
                                <th
                                    className="px-5 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider cursor-pointer select-none hover:text-surface-700 transition"
                                    onClick={() => toggleSort('name')}
                                >
                                    <span className="inline-flex items-center gap-1">
                                        Facility Name <ArrowUpDown className="w-3 h-3" />
                                    </span>
                                </th>
                                <th className="px-5 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Type</th>
                                <th className="px-5 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">District</th>
                                <th className="px-5 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Risk Level</th>
                                <th
                                    className="px-5 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider cursor-pointer select-none hover:text-surface-700 transition"
                                    onClick={() => toggleSort('crs')}
                                >
                                    <span className="inline-flex items-center gap-1">
                                        CRS <ArrowUpDown className="w-3 h-3" />
                                    </span>
                                </th>
                                <th className="px-5 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Status</th>
                                <th className="px-5 py-3 text-right text-xs font-semibold text-surface-500 uppercase tracking-wider">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-surface-100">
                            {paginated.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="px-5 py-12 text-center text-surface-400">
                                        No facilities match your search criteria
                                    </td>
                                </tr>
                            ) : (
                                paginated.map(f => {
                                    const crsPercent = Math.round(f.crs * 100)
                                    const status = statusFromAlert(f)
                                    return (
                                        <tr key={f.facility_id} className="hover:bg-surface-50/50 transition">
                                            <td className="px-5 py-3.5 font-medium text-surface-800">{f.facility_name}</td>
                                            <td className="px-5 py-3.5 text-surface-600">
                                                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${f.facility_type === 'School' ? 'bg-blue-50 text-blue-700' : 'bg-purple-50 text-purple-700'
                                                    }`}>
                                                    {f.facility_type}
                                                </span>
                                            </td>
                                            <td className="px-5 py-3.5 text-surface-600">{f.district}</td>
                                            <td className="px-5 py-3.5">{riskBadge(f.risk_level)}</td>
                                            <td className="px-5 py-3.5">
                                                <div className="flex items-center gap-2">
                                                    <div className="flex-1 max-w-[80px] h-1.5 rounded-full bg-surface-200 overflow-hidden">
                                                        <div
                                                            className="h-full rounded-full transition-all"
                                                            style={{
                                                                width: `${crsPercent}%`,
                                                                backgroundColor: f.risk_level === 'High' ? '#ef4444' : f.risk_level === 'Medium' ? '#f97316' : '#22c55e',
                                                            }}
                                                        />
                                                    </div>
                                                    <span className="text-xs font-semibold text-surface-700 w-8">{crsPercent}%</span>
                                                </div>
                                            </td>
                                            <td className="px-5 py-3.5">
                                                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${status === 'Action Required' ? 'bg-red-50 text-red-700' :
                                                    status === 'Under Review' ? 'bg-amber-50 text-amber-700' :
                                                        'bg-emerald-50 text-emerald-700'
                                                    }`}>
                                                    {status}
                                                </span>
                                            </td>
                                            <td className="px-5 py-3.5 text-right">
                                                <Link
                                                    to={`/facilities/${encodeURIComponent(f.facility_id)}`}
                                                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-primary-600 bg-primary-50 rounded-lg hover:bg-primary-100 transition"
                                                >
                                                    View Details
                                                </Link>
                                            </td>
                                        </tr>
                                    )
                                })
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-between px-5 py-3 border-t border-surface-100 bg-surface-50/30">
                    <p className="text-xs text-surface-500">
                        Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length} facilities
                    </p>
                    <div className="flex items-center gap-1">
                        <button
                            disabled={page === 1}
                            onClick={() => setPage(p => p - 1)}
                            className="p-1.5 rounded-lg hover:bg-surface-200 disabled:opacity-30 disabled:hover:bg-transparent transition"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => i + 1).map(p => (
                            <button
                                key={p}
                                onClick={() => setPage(p)}
                                className={`w-8 h-8 rounded-lg text-xs font-semibold transition ${page === p ? 'bg-primary-600 text-white shadow-md' : 'text-surface-600 hover:bg-surface-200'
                                    }`}
                            >
                                {p}
                            </button>
                        ))}
                        {totalPages > 7 && <span className="text-xs text-surface-400 px-1">...</span>}
                        {totalPages > 7 && (
                            <button
                                onClick={() => setPage(totalPages)}
                                className={`w-8 h-8 rounded-lg text-xs font-semibold transition ${page === totalPages ? 'bg-primary-600 text-white shadow-md' : 'text-surface-600 hover:bg-surface-200'}`}
                            >
                                {totalPages}
                            </button>
                        )}
                        <button
                            disabled={page === totalPages}
                            onClick={() => setPage(p => p + 1)}
                            className="p-1.5 rounded-lg hover:bg-surface-200 disabled:opacity-30 disabled:hover:bg-transparent transition"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
