import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
    LayoutDashboard,
    Map,
    Building2,
    AlertTriangle,
    Settings,
    Bell,
    User,
    Menu,
    X,
    Shield,
    ChevronRight,
    BrainCircuit,
    Activity,
    TrendingUp,
} from 'lucide-react'

const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/map', icon: Map, label: 'Risk Map' },
    { to: '/simulator', icon: Activity, label: 'Simulator' },
    { to: '/prioritization', icon: TrendingUp, label: 'Prioritization' },
    { to: '/facilities', icon: Building2, label: 'Facilities' },
    { to: '/xai', icon: BrainCircuit, label: 'AI Explain' },
    { to: '/alerts', icon: AlertTriangle, label: 'Alerts' },
    { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function AppLayout() {
    const [sidebarOpen, setSidebarOpen] = useState(false)

    return (
        <div className="flex h-screen overflow-hidden bg-surface-50">
            {/* Mobile overlay */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside
                className={`
          fixed inset-y-0 left-0 z-50 w-[260px] flex flex-col
          bg-gradient-to-b from-surface-900 to-surface-950 text-white
          transition-transform duration-300 ease-in-out
          lg:relative lg:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
            >
                {/* Logo */}
                <div className="flex items-center gap-3 px-6 py-5 border-b border-white/10">
                    <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 shadow-lg shadow-primary-500/30">
                        <Shield className="w-5 h-5" />
                    </div>
                    <div>
                        <h1 className="text-lg font-bold tracking-tight">ClimaSafe</h1>
                        <p className="text-[11px] text-surface-400 font-medium tracking-wide uppercase">Risk Monitor</p>
                    </div>
                    <button
                        className="ml-auto lg:hidden p-1 rounded-lg hover:bg-white/10 transition"
                        onClick={() => setSidebarOpen(false)}
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Nav */}
                <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
                    {navItems.map(item => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            end={item.to === '/'}
                            onClick={() => setSidebarOpen(false)}
                            className={({ isActive }) =>
                                `group flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200
                ${isActive
                                    ? 'bg-white/15 text-white shadow-lg shadow-black/10'
                                    : 'text-surface-400 hover:text-white hover:bg-white/8'
                                }`
                            }
                        >
                            {({ isActive }) => (
                                <>
                                    <item.icon className={`w-[18px] h-[18px] transition ${isActive ? 'text-primary-400' : 'text-surface-500 group-hover:text-surface-300'}`} />
                                    <span>{item.label}</span>
                                    {isActive && <ChevronRight className="w-4 h-4 ml-auto text-primary-400" />}
                                </>
                            )}
                        </NavLink>
                    ))}
                </nav>

                {/* Bottom */}
                <div className="px-4 py-4 border-t border-white/10">
                    <div className="flex items-center gap-3 px-3 py-2 rounded-xl bg-white/5">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-xs font-bold">
                            GA
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">Gov Admin</p>
                            <p className="text-[11px] text-surface-500 truncate">admin@climasafe.gov.in</p>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main content area */}
            <div className="flex flex-col flex-1 min-w-0">
                {/* Top Navbar */}
                <header className="sticky top-0 z-30 flex items-center gap-4 px-4 sm:px-6 py-3 bg-white/80 backdrop-blur-xl border-b border-surface-200/60">
                    <button
                        className="lg:hidden p-2 rounded-xl hover:bg-surface-100 transition"
                        onClick={() => setSidebarOpen(true)}
                    >
                        <Menu className="w-5 h-5 text-surface-600" />
                    </button>

                    <div className="flex-1 min-w-0">
                        <h2 className="text-base font-semibold text-surface-800 truncate">
                            Infrastructure Risk Monitoring System
                        </h2>
                        <p className="text-xs text-surface-500 hidden sm:block">
                            AI-powered climate risk assessment for schools &amp; health facilities
                        </p>
                    </div>

                    <div className="flex items-center gap-2">
                        <button className="relative p-2.5 rounded-xl hover:bg-surface-100 transition group">
                            <Bell className="w-5 h-5 text-surface-500 group-hover:text-surface-700 transition" />
                            <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-risk-high rounded-full ring-2 ring-white" />
                        </button>
                        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-primary-500/20 cursor-pointer">
                            A
                        </div>
                    </div>
                </header>

                {/* Page content */}
                <main className="flex-1 overflow-y-auto p-4 sm:p-6">
                    <Outlet />
                </main>
            </div>
        </div>
    )
}
