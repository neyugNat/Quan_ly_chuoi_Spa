import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './auth/ProtectedRoute.jsx'
import { useAuth } from './auth/AuthContext.jsx'
import { getFirstAllowedPath } from './auth/navConfig.js'
import { AppLayout } from './layout/AppLayout.jsx'
import { DashboardPage } from './pages/DashboardPage.jsx'
import { LoginPage } from './pages/LoginPage.jsx'
import { UnauthorizedPage } from './pages/UnauthorizedPage.jsx'
import { CustomersPage } from './pages/CustomersPage.jsx'
import { AppointmentsPage } from './pages/AppointmentsPage.jsx'
import { ServicesPage } from './pages/ServicesPage.jsx'
import { PackagesPage } from './pages/PackagesPage.jsx'
import { ReportsPage } from './pages/ReportsPage.jsx'
import { AuditLogsPage } from './pages/AuditLogsPage.jsx'
import { InventoryPage } from './pages/InventoryPage.jsx'
import { PosPage } from './pages/PosPage.jsx'
import { HrPage } from './pages/HrPage.jsx'
import { TechnicianPage } from './pages/TechnicianPage.jsx'
import { BranchesPage } from './pages/BranchesPage.jsx'
import { ResourcesPage } from './pages/ResourcesPage.jsx'
import { UsersPage } from './pages/UsersPage.jsx'

function HomeRedirect() {
  const { booted, user } = useAuth()
  if (!booted) return null
  return <Navigate to={getFirstAllowedPath(user)} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/unauthorized" element={<UnauthorizedPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route element={<ProtectedRoute allowedRoles={['super_admin', 'branch_manager']} />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/services" element={<ServicesPage />} />
            <Route path="/packages" element={<PackagesPage />} />
            <Route path="/resources" element={<ResourcesPage />} />
            <Route path="/hr" element={<HrPage />} />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={['super_admin', 'branch_manager', 'reception', 'cashier']} />}>
            <Route path="/customers" element={<CustomersPage />} />
            <Route path="/pos" element={<PosPage />} />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={['super_admin', 'branch_manager', 'warehouse']} />}>
            <Route path="/inventory" element={<InventoryPage />} />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={['super_admin', 'branch_manager', 'reception']} />}>
            <Route path="/appointments" element={<AppointmentsPage />} />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={['super_admin']} />}>
            <Route path="/audit-logs" element={<AuditLogsPage />} />
            <Route path="/branches" element={<BranchesPage />} />
            <Route path="/users" element={<UsersPage />} />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={['technician']} />}>
            <Route path="/technician" element={<TechnicianPage />} />
          </Route>

          <Route path="/" element={<HomeRedirect />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
