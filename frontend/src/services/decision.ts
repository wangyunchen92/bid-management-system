import { get, post, put, del } from '@/utils/request';
import { DECISION_API } from '@/constants/api';

export function getDecisionList(params?: Record<string, unknown>) {
  return get<PaginatedData<BidDecision>>(DECISION_API.LIST, params);
}
export function createDecision(data: Record<string, unknown>) {
  return post<BidDecision>(DECISION_API.CREATE, data);
}
export function getDecision(id: number) {
  return get<BidDecision>(DECISION_API.DETAIL(id));
}
export function updateDecision(id: number, data: Record<string, unknown>) {
  return put<BidDecision>(DECISION_API.UPDATE(id), data);
}
export function deleteDecision(id: number) {
  return del(DECISION_API.DELETE(id));
}
export function getDecisionByTender(tenderId: number) {
  return get<BidDecision[]>(DECISION_API.BY_TENDER(tenderId));
}
