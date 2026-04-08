import { get, post, put, del } from '@/utils/request';
import { SYSTEM_API } from '@/constants/api';

export function getDictTypeList(params?: Record<string, unknown>) {
  return get<PaginatedData<DictType>>(SYSTEM_API.DICT_TYPE_LIST, params);
}
export function createDictType(data: Partial<DictType>) {
  return post<DictType>(SYSTEM_API.DICT_TYPE_CREATE, data);
}
export function updateDictType(id: number, data: Partial<DictType>) {
  return put<DictType>(SYSTEM_API.DICT_TYPE_UPDATE(id), data);
}
export function deleteDictType(id: number) {
  return del(SYSTEM_API.DICT_TYPE_DELETE(id));
}
export function getDictItemList(typeId: number) {
  return get<DictItem[]>(SYSTEM_API.DICT_ITEM_LIST(typeId));
}
export function createDictItem(typeId: number, data: Partial<DictItem>) {
  return post<DictItem>(SYSTEM_API.DICT_ITEM_CREATE(typeId), data);
}
export function updateDictItem(id: number, data: Partial<DictItem>) {
  return put<DictItem>(SYSTEM_API.DICT_ITEM_UPDATE(id), data);
}
export function deleteDictItem(id: number) {
  return del(SYSTEM_API.DICT_ITEM_DELETE(id));
}
export function getDictByCode(code: string) {
  return get<DictItem[]>(SYSTEM_API.DICT_BY_CODE(code));
}
