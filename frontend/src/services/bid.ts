import { get, post, put, del } from '@/utils/request';
import request from '@/utils/request';
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

export function aiGenerateSection(sectionId: number, data: { tender_requirements?: string; additional_context?: string }) {
  return post<{ generated_content: string }>(BID_API.SECTION_AI_GENERATE(sectionId), data);
}

export async function aiGenerateSectionStream(
  sectionId: number,
  data: { tender_requirements?: string; additional_context?: string },
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
) {
  const token = localStorage.getItem('bid_system_access_token');
  const response = await fetch(BID_API.SECTION_AI_GENERATE_STREAM(sectionId), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    onError(`请求失败: ${response.status}`);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) { onError('无法读取响应流'); return; }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const json = JSON.parse(line.slice(6));
          if (json.content) onChunk(json.content);
          if (json.done) onDone();
          if (json.error) onError(json.error);
        } catch { /* skip */ }
      }
    }
  }
  onDone();
}

export function bidComplianceCheck(projectId: number, data: { tender_requirements?: string }) {
  return post<BidCheckResult>(BID_API.PROJECT_CHECK(projectId), data);
}

export function exportBidWord(projectId: number) {
  return request.get(BID_API.PROJECT_EXPORT(projectId), {
    responseType: 'blob',
  });
}
