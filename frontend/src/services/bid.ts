import { get, post, put, del } from '@/utils/request';
import { BID_API } from '@/constants/api';

// ── 标书项目 ──────────────────────────────────────────────────

export function getBidProjectList(params?: Record<string, unknown>) {
  return get<PaginatedData<BidProject>>(BID_API.PROJECT_LIST, params);
}

export function createBidProject(data: Partial<BidProject>) {
  return post<BidProject>(BID_API.PROJECT_CREATE, data);
}

export function getBidProject(id: number) {
  return get<BidProject>(BID_API.PROJECT_DETAIL(id));
}

export function updateBidProject(id: number, data: Partial<BidProject>) {
  return put<BidProject>(BID_API.PROJECT_UPDATE(id), data);
}

export function deleteBidProject(id: number) {
  return del(BID_API.PROJECT_DELETE(id));
}

export function getBidProjectByTender(tenderId: number) {
  return get<BidProject>(BID_API.PROJECT_BY_TENDER(tenderId));
}

// ── 标书章节 ──────────────────────────────────────────────────

export function getSectionTree(projectId: number) {
  return get<BidSection[]>(BID_API.SECTION_TREE(projectId));
}

export function createSection(data: Partial<BidSection> & { project_id: number; title: string }) {
  return post<BidSection>(BID_API.SECTION_CREATE, data);
}

export function getSection(id: number) {
  return get<BidSection>(BID_API.SECTION_DETAIL(id));
}

export function updateSection(id: number, data: Partial<BidSection>) {
  return put<BidSection>(BID_API.SECTION_UPDATE(id), data);
}

export function deleteSection(id: number) {
  return del(BID_API.SECTION_DELETE(id));
}

export function reorderSections(projectId: number, items: { id: number; sort_order: number; parent_id?: number }[]) {
  return post<null>(BID_API.SECTION_REORDER(projectId), { items });
}
