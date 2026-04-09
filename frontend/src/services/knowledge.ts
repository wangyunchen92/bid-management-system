import { get, post, put, del } from '@/utils/request';
import { KNOWLEDGE_API } from '@/constants/api';

export function getKnowledgeList(params?: Record<string, unknown>) {
  return get<PaginatedData<KnowledgeTemplate>>(KNOWLEDGE_API.LIST, params);
}

export function createKnowledge(data: Partial<KnowledgeTemplate>) {
  return post<KnowledgeTemplate>(KNOWLEDGE_API.CREATE, data);
}

export function getKnowledge(id: number) {
  return get<KnowledgeTemplate>(KNOWLEDGE_API.DETAIL(id));
}

export function updateKnowledge(id: number, data: Partial<KnowledgeTemplate>) {
  return put<KnowledgeTemplate>(KNOWLEDGE_API.UPDATE(id), data);
}

export function deleteKnowledge(id: number) {
  return del(KNOWLEDGE_API.DELETE(id));
}

export function searchKnowledge(params?: Record<string, unknown>) {
  return get<KnowledgeTemplate[]>(KNOWLEDGE_API.SEARCH, params);
}
