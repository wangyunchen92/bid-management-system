export function getAccessMap(currentUser: CurrentUser | null): Record<string, boolean> {
  if (!currentUser) return {};

  const isSuperAdmin = currentUser.role === 'SUPER_ADMIN';

  return {
    isSuperAdmin,
    canAccessSystem: isSuperAdmin,
    canAccessDashboard: true,
  };
}
