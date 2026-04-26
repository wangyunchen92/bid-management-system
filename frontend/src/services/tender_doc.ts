import { get, post, del } from '@/utils/request';
import { TENDER_DOC_API } from '@/constants/api';
import request from '@/utils/request';

export interface UploadProgressEvent {
  type: 'uploading' | 'extracting' | 'ocr_start' | 'ocr_page' | 'ocr_page_failed' | 'ocr_done'
      | 'parsing' | 'linking' | 'linked' | 'link_failed' | 'done' | 'error';
  message?: string;
  total_pages?: number;
  pages_to_process?: number;
  current?: number;
  total?: number;
  page?: number;
  doc?: TenderDocumentInfo;
  tender_id?: number;
  action?: string;
  error?: string;
}

/**
 * 上传招标文件（SSE 流式版本）
 * @returns 最终解析完成的 doc info（done 事件中的 doc）
 */
export async function uploadTenderDocStream(
  file: File,
  projectId: number | undefined,
  tenderId: number | undefined,
  onProgress: (event: UploadProgressEvent) => void,
): Promise<TenderDocumentInfo> {
  const formData = new FormData();
  formData.append('file', file);
  const params = new URLSearchParams();
  if (projectId) params.append('project_id', String(projectId));
  if (tenderId) params.append('tender_id', String(tenderId));
  const url = params.toString() ? `${TENDER_DOC_API.UPLOAD}?${params}` : TENDER_DOC_API.UPLOAD;

  const token = localStorage.getItem('bid_system_access_token');
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('无法读取响应流');

  const decoder = new TextDecoder();
  let buffer = '';
  let finalDoc: TenderDocumentInfo | null = null;
  let errorMsg: string | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event = JSON.parse(line.slice(6)) as UploadProgressEvent;
          onProgress(event);
          if (event.type === 'done' && event.doc) finalDoc = event.doc;
          if (event.type === 'error') errorMsg = event.message || event.error || '解析失败';
        } catch { /* skip */ }
      }
    }
  }

  if (errorMsg) throw new Error(errorMsg);
  if (!finalDoc) throw new Error('未收到解析完成事件');
  return finalDoc;
}

/** @deprecated 使用 uploadTenderDocStream */
export function uploadTenderDoc(file: File, projectId?: number, tenderId?: number) {
  const formData = new FormData();
  formData.append('file', file);
  const params = new URLSearchParams();
  if (projectId) params.append('project_id', String(projectId));
  if (tenderId) params.append('tender_id', String(tenderId));
  const url = params.toString() ? `${TENDER_DOC_API.UPLOAD}?${params}` : TENDER_DOC_API.UPLOAD;
  return request.post<unknown, ApiResponse<TenderDocumentInfo>>(url, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 1800000, // 30分钟超时（OCR 100 页可能很慢）
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
