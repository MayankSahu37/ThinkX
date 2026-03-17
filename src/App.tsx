import { Routes, Route } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import Dashboard from './pages/Dashboard'
import RiskMap from './pages/RiskMap'
import Facilities from './pages/Facilities'
import FacilityDetail from './pages/FacilityDetail'
import Alerts from './pages/Alerts'
import Settings from './pages/Settings'
import XAIAnalysis from './pages/XAIAnalysis'
import Simulator from './pages/Simulator'
import Prioritization from './pages/Prioritization'

export default function App() {
    return (
        <Routes>
            <Route element={<AppLayout />}>
                <Route index element={<Dashboard />} />
                <Route path="map" element={<RiskMap />} />
                <Route path="facilities" element={<Facilities />} />
                <Route path="facilities/:id" element={<FacilityDetail />} />
                <Route path="simulator" element={<Simulator />} />
                <Route path="prioritization" element={<Prioritization />} />
                <Route path="xai" element={<XAIAnalysis />} />
                <Route path="alerts" element={<Alerts />} />
                <Route path="settings" element={<Settings />} />
            </Route>
        </Routes>
    )
}
