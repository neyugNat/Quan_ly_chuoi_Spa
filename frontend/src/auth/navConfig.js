export const NAV = [
  { to: '/dashboard', label: 'Tổng quan', roles: ['super_admin', 'branch_manager'] },
  { to: '/pos', label: 'POS / Hóa đơn', roles: ['super_admin', 'branch_manager', 'reception', 'cashier'] },
  { to: '/customers', label: 'Khách hàng', roles: ['super_admin', 'branch_manager', 'reception', 'cashier'] },
  { to: '/appointments', label: 'Lịch hẹn', roles: ['super_admin', 'branch_manager', 'reception'] },
  { to: '/services', label: 'Dịch vụ', roles: ['super_admin', 'branch_manager'] },
  { to: '/packages', label: 'Gói liệu trình', roles: ['super_admin', 'branch_manager'] },
  { to: '/resources', label: 'Tài nguyên', roles: ['super_admin', 'branch_manager'] },
  { to: '/inventory', label: 'Kho', roles: ['super_admin', 'branch_manager', 'warehouse'] },
  { to: '/hr', label: 'Nhân sự', roles: ['super_admin', 'branch_manager'] },
  { to: '/reports', label: 'Báo cáo', roles: ['super_admin', 'branch_manager'] },
  { to: '/users', label: 'Tài khoản', roles: ['super_admin'] },
  { to: '/branches', label: 'Chi nhánh', roles: ['super_admin'] },
  { to: '/audit-logs', label: 'Nhật ký hệ thống', roles: ['super_admin'] },
  { to: '/technician', label: 'Kỹ thuật viên', roles: ['technician'] },
]

export function canSeeRoles(userRoles, allowedRoles) {
  if (!allowedRoles || allowedRoles.length === 0) return true
  const normalizedUserRoles = (userRoles || []).map(String)
  return normalizedUserRoles.some((role) => allowedRoles.includes(role))
}

export function getFirstAllowedPath(user) {
  const first = NAV.find((item) => canSeeRoles(user?.roles, item.roles))
  return first?.to || '/login'
}
