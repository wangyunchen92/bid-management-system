import { get, post, put, del } from '@/utils/request';
import { TENDER_API } from '@/constants/api';

export function getTenderList(params?: Record<string, unknown>) {
  return get<PaginatedData<Tender>>(TENDER_API.LIST, params);
}
export function createTender(data: Partial<Tender>) {
  return post<Tender>(TENDER_API.CREATE, data);
}
export function getTender(id: number) {
  return get<Tender>(TENDER_API.DETAIL(id));
}
export function updateTender(id: number, data: Partial<Tender>) {
  return put<Tender>(TENDER_API.UPDATE(id), data);
}
export function deleteTender(id: number) {
  return del(TENDER_API.DELETE(id));
}
export function updateTenderStatus(id: number, status: string) {
  return put<Tender>(TENDER_API.UPDATE_STATUS(id), { status });
}
export function updateTenderFollower(id: number, followerId: number) {
  return put<Tender>(TENDER_API.UPDATE_FOLLOWER(id), { follower_id: followerId });
}
export function getTenderCalendar(year: number, month: number) {
  return get<TenderCalendarItem[]>(TENDER_API.CALENDAR, { year, month });
}
export function getTenderStats() {
  return get<TenderStats>(TENDER_API.STATS);
}
export function getTenderExpiring() {
  return get<Tender[]>(TENDER_API.EXPIRING);
}
