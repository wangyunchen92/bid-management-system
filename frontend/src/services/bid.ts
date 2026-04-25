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

export function generateBidFramework(projectId: number) {
  return post<any[]>(BID_API.PROJECT_GENERATE_FRAMEWORK(projectId));
}

export async function generateFrameworkFromTender(
  projectId: number,
  tenderDocId: number,
  onExtractStart: (chapterCount: number) => void,
  onExtractDone: (matchedCount: number, durationMs: number) => void,
  onExtractFailed: (message: string, durationMs: number) => void,
  onSectionCreated: (title: string, sectionType: string, hasContent: boolean) => void,
  onDone: (total: number, withContent: number) => void,
  onError: (message: string) => void,
) {
  const token = localStorage.getItem('bid_system_access_token');
  const response = await fetch(BID_API.PROJECT_FRAMEWORK_FROM_TENDER(projectId), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ tender_doc_id: tenderDocId }),
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
      if (!line.startsWith('data: ')) continue;
      try {
        const data = JSON.parse(line.slice(6));
        switch (data.type) {
          case 'extract_start': onExtractStart(data.chapter_count); break;
          case 'extract_done': onExtractDone(data.matched_count, data.duration_ms); break;
          case 'extract_failed': onExtractFailed(data.message, data.duration_ms); break;
          case 'section_created': onSectionCreated(data.title, data.section_type, data.has_content); break;
          case 'done': onDone(data.total, data.with_content); break;
          case 'error': onError(data.message); break;
        }
      } catch { /* skip */ }
    }
  }
}

export function fillLibrarySections(projectId: number) {
  return post<Array<{ id: number; title: string; word_count: number }>>(BID_API.PROJECT_FILL_LIBRARY(projectId));
}

export async function batchAiGenerate(
  projectId: number,
  onProgress: (current: number, total: number, title: string) => void,
  onSectionDone: (sectionId: number, title: string, wordCount: number) => void,
  onDone: (total: number) => void,
  onError: (title: string, err: string) => void,
) {
  const token = localStorage.getItem('bid_system_access_token');
  const response = await fetch(BID_API.PROJECT_BATCH_AI(projectId), {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
  });

  if (!response.ok) {
    onError('', `请求失败: ${response.status}`);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) { onError('', '无法读取响应流'); return; }

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
          const data = JSON.parse(line.slice(6));
          if (data.type === 'progress') onProgress(data.current, data.total, data.section_title);
          if (data.type === 'section_done') onSectionDone(data.section_id, data.section_title, data.word_count);
          if (data.type === 'section_error') onError(data.section_title, data.error);
          if (data.type === 'done') onDone(data.total);
        } catch { /* skip */ }
      }
    }
  }
}

export function previewBidDocument(projectId: number) {
  return get<{
    project_title: string;
    total_sections: number;
    completed_sections: number;
    total_words: number;
    sections: Array<{
      id: number;
      title: string;
      content: string;
      section_type: string;
      status: string;
      word_count: number;
      sort_order: number;
    }>;
  }>(BID_API.PROJECT_PREVIEW(projectId));
}

export function bidComplianceCheck(projectId: number, data: { tender_requirements?: string }) {
  return post<BidCheckResult>(BID_API.PROJECT_CHECK(projectId), data);
}

export function exportBidWord(projectId: number) {
  return request.get(BID_API.PROJECT_EXPORT(projectId), {
    responseType: 'blob',
  });
}

// ── 标书检测 ──────────────────────────────────────────────────

export interface DetectItem {
  category: string;
  check_name: string;
  status: 'PASS' | 'WARNING' | 'FAIL';
  source: string | null;
  detail: string;
  suggestion: string | null;
  section_title: string | null;
}

export interface DetectReport {
  id: number;
  project_id: number;
  total_score: number;
  status: string;
  rule_score: number;
  ai_score: number;
  rule_items: DetectItem[];
  ai_items: DetectItem[];
  summary: string | null;
  created_at: string | null;
  created_by: number | null;
}

export interface DetectReportListItem {
  id: number;
  total_score: number;
  status: string;
  summary: string | null;
  created_at: string | null;
}

export async function runBidDetection(
  projectId: number,
  onRuleItem: (item: DetectItem) => void,
  onRuleDone: (ruleScore: number, count: number) => void,
  onAiStart: (category: string, current: number, total: number) => void,
  onAiItem: (item: DetectItem) => void,
  onAiCategoryDone: (category: string, score: number) => void,
  onDone: (reportId: number, totalScore: number, status: string, summary: string) => void,
  onError: (err: string) => void,
) {
  const token = localStorage.getItem('bid_system_access_token');
  const response = await fetch(BID_API.PROJECT_DETECT(projectId), {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
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
          const data = JSON.parse(line.slice(6));
          switch (data.type) {
            case 'rule_item': onRuleItem(data.item); break;
            case 'rule_done': onRuleDone(data.rule_score, data.count); break;
            case 'ai_start': onAiStart(data.category, data.current, data.total); break;
            case 'ai_item': onAiItem(data.item); break;
            case 'ai_category_done': onAiCategoryDone(data.category, data.score); break;
            case 'done': onDone(data.report_id, data.total_score, data.status, data.summary); break;
          }
        } catch { /* skip */ }
      }
    }
  }
}

export function getDetectReports(projectId: number) {
  return get<DetectReportListItem[]>(BID_API.PROJECT_DETECT_REPORTS(projectId));
}

export function getDetectReportDetail(projectId: number, reportId: number) {
  return get<DetectReport>(BID_API.PROJECT_DETECT_REPORT_DETAIL(projectId, reportId));
}
