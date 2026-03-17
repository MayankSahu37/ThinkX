import { Settings as SettingsIcon, Bell, Shield, Database, Globe, User } from 'lucide-react'

export default function Settings() {
    return (
        <div className="space-y-6 max-w-4xl">
            <div>
                <h1 className="text-2xl font-bold text-surface-900 flex items-center gap-2">
                    <SettingsIcon className="w-6 h-6 text-primary-500" /> Settings
                </h1>
                <p className="text-sm text-surface-500 mt-1">Configure your risk monitoring preferences</p>
            </div>

            <div className="space-y-4">
                {/* Notifications */}
                <div className="bg-white rounded-2xl border border-surface-200/60 p-5 shadow-sm">
                    <h3 className="text-sm font-semibold text-surface-700 mb-4 flex items-center gap-2">
                        <Bell className="w-4 h-4 text-primary-500" /> Notification Preferences
                    </h3>
                    <div className="space-y-4">
                        {['High-risk alerts', 'Medium-risk alerts', 'Weekly summary reports', 'System status updates'].map((item, i) => (
                            <div key={i} className="flex items-center justify-between py-2">
                                <span className="text-sm text-surface-700">{item}</span>
                                <button className={`relative w-11 h-6 rounded-full transition-colors ${i < 2 ? 'bg-primary-500' : 'bg-surface-300'}`}>
                                    <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform ${i < 2 ? 'left-5.5' : 'left-0.5'}`} />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Risk Thresholds */}
                <div className="bg-white rounded-2xl border border-surface-200/60 p-5 shadow-sm">
                    <h3 className="text-sm font-semibold text-surface-700 mb-4 flex items-center gap-2">
                        <Shield className="w-4 h-4 text-amber-500" /> Risk Thresholds
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {[{ label: 'High Risk', value: '75', color: 'red' }, { label: 'Medium Risk', value: '40', color: 'orange' }, { label: 'Low Risk', value: '0', color: 'emerald' }].map(t => (
                            <div key={t.label} className={`p-4 bg-${t.color}-50 rounded-xl border border-${t.color}-200/60`}>
                                <p className={`text-xs font-semibold text-${t.color}-700 mb-2`}>{t.label} Threshold</p>
                                <input
                                    type="number"
                                    defaultValue={t.value}
                                    className="w-full px-3 py-2 text-sm rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/30 bg-white"
                                />
                            </div>
                        ))}
                    </div>
                </div>

                {/* API Configuration */}
                <div className="bg-white rounded-2xl border border-surface-200/60 p-5 shadow-sm">
                    <h3 className="text-sm font-semibold text-surface-700 mb-4 flex items-center gap-2">
                        <Database className="w-4 h-4 text-purple-500" /> API Configuration
                    </h3>
                    <div className="space-y-3">
                        <div>
                            <label className="text-xs font-medium text-surface-600 mb-1 block">Backend API URL</label>
                            <input
                                type="text"
                                defaultValue="http://localhost:8000"
                                className="w-full px-3 py-2 text-sm rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/30 bg-white"
                            />
                        </div>
                        <div>
                            <label className="text-xs font-medium text-surface-600 mb-1 block">Data Refresh Interval</label>
                            <select className="w-full px-3 py-2 text-sm rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/30 bg-white">
                                <option>Every 5 minutes</option>
                                <option>Every 15 minutes</option>
                                <option>Every 30 minutes</option>
                                <option>Every hour</option>
                            </select>
                        </div>
                    </div>
                </div>

                {/* Profile */}
                <div className="bg-white rounded-2xl border border-surface-200/60 p-5 shadow-sm">
                    <h3 className="text-sm font-semibold text-surface-700 mb-4 flex items-center gap-2">
                        <User className="w-4 h-4 text-emerald-500" /> Profile
                    </h3>
                    <div className="flex items-center gap-4 mb-4">
                        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white text-xl font-bold shadow-lg shadow-primary-500/20">
                            GA
                        </div>
                        <div>
                            <p className="font-semibold text-surface-800">Government Admin</p>
                            <p className="text-sm text-surface-500">admin@climasafe.gov.in</p>
                        </div>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label className="text-xs font-medium text-surface-600 mb-1 block">Full Name</label>
                            <input type="text" defaultValue="Government Admin" className="w-full px-3 py-2 text-sm rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/30 bg-white" />
                        </div>
                        <div>
                            <label className="text-xs font-medium text-surface-600 mb-1 block">Email</label>
                            <input type="email" defaultValue="admin@climasafe.gov.in" className="w-full px-3 py-2 text-sm rounded-lg border border-surface-200 focus:outline-none focus:ring-2 focus:ring-primary-500/30 bg-white" />
                        </div>
                    </div>
                </div>

                <button className="px-6 py-2.5 bg-primary-600 text-white text-sm font-semibold rounded-xl hover:bg-primary-700 transition shadow-lg shadow-primary-500/20">
                    Save Changes
                </button>
            </div>
        </div>
    )
}
