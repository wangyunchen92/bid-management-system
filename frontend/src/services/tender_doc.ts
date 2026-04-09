import { get, post, del } from '@/utils/request';
import { TENDER_DOC_API } from '@/constants/api';
import request from '@/utils/request';

export function uploadTenderDoc(file: File, projectId?: number, tenderId?: number) {
  const formData = new FormData();
  formData.append('file', file);
  const params = new URLSearchParams();
  if (projectId) params.append('project_id', String(projectId));
  if (tenderId) params.append('tender_id', String(tenderId));
  const url = params.toString() ? `${TENDER_DOC_API.UPLOAD}?${params}` : TENDER_DOC_API.UPLOAD;
  return request.post<unknown, ApiResponse<TenderDocumentInfo>>(url, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000, // 2分钟超时（AI解析需要时间）
  });
}

export function getTenderDoc(id: number) {
  return get<TenderDocumentInfo>(TENDER_DOC_API.DETAIL(id));
}

export function getTenderDocsByProject(projectId: number) {
  return get<TenderDocumentInfo[]>(TENDER_DOC_API.BY_PROJECT(projectId));
}

export function getTenderDocsByTender(tenderId: number) {
  return get<TenderDocumentInfo[]>(TENDER_DOC_API.BY_TENDER(tenderId));
}

export function deleteTenderDoc(id: number) {
  return del(TENDER_DOC_API.DELETE(id));
}

export function saveToTender(docId: number) {
  return post<{ tender_id: number; action: string; fields_updated: string[] }>(TENDER_DOC_API.SAVE_TO_TENDER(docId));
}
