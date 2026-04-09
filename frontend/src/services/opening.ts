import { get, post, put, del } from '@/utils/request';
import { OPENING_API } from '@/constants/api';

export function getOpeningList(params?: Record<string, unknown>) {
  return get<PaginatedData<BidOpening>>(OPENING_API.LIST, params);
}
export function createOpening(data: Record<string, unknown>) {
  return post<BidOpening>(OPENING_API.CREATE, data);
}
export function getOpening(id: number) {
  return get<BidOpening>(OPENING_API.DETAIL(id));
}
export function updateOpening(id: number, data: Record<string, unknown>) {
  return put<BidOpening>(OPENING_API.UPDATE(id), data);
}
export function deleteOpening(id: number) {
  return del(OPENING_API.DELETE(id));
}
export function getOpeningByTender(tenderId: number) {
  return get<BidOpening[]>(OPENING_API.BY_TENDER(tenderId));
}
