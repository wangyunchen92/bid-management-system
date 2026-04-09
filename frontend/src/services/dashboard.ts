import { get } from '@/utils/request';
import { DASHBOARD_API } from '@/constants/api';

export function getDashboardStats() {
  return get<DashboardStats>(DASHBOARD_API.STATS);
}
