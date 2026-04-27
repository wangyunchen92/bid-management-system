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

// ========== 部门 ==========

export function getDepartmentTree() {
  return get<Department[]>(SYSTEM_API.DEPT_TREE);
}

export function createDepartment(data: Partial<Department>) {
  return post<Department>(SYSTEM_API.DEPT_CREATE, data);
}

export function getDepartment(id: number) {
  return get<Department>(SYSTEM_API.DEPT_DETAIL(id));
}

export function updateDepartment(id: number, data: Partial<Department>) {
  return put<Department>(SYSTEM_API.DEPT_UPDATE(id), data);
}

export function deleteDepartment(id: number) {
  return del(SYSTEM_API.DEPT_DELETE(id));
}

// ========== 用户 ==========

export function getUserList(params?: Record<string, unknown>) {
  return get<PaginatedData<SystemUser>>(SYSTEM_API.USER_LIST, params);
}

export function createUser(data: Record<string, unknown>) {
  return post<SystemUser>(SYSTEM_API.USER_CREATE, data);
}

export function updateUser(id: number, data: Record<string, unknown>) {
  return put<SystemUser>(SYSTEM_API.USER_UPDATE(id), data);
}

export function deleteUser(id: number) {
  return del(SYSTEM_API.USER_DELETE(id));
}

export function resetUserPassword(id: number) {
  return put(SYSTEM_API.USER_RESET_PWD(id));
}

// ========== 角色 ==========

export function getRoleList() {
  return get<SysRole[]>(SYSTEM_API.ROLE_LIST);
}

export function createRole(data: Partial<SysRole>) {
  return post<SysRole>(SYSTEM_API.ROLE_CREATE, data);
}

export function updateRole(id: number, data: Partial<SysRole>) {
  return put<SysRole>(SYSTEM_API.ROLE_UPDATE(id), data);
}

export function deleteRole(id: number) {
  return del(SYSTEM_API.ROLE_DELETE(id));
}

export function getUserRoles(userId: number) {
  return get<UserRoleInfo[]>(SYSTEM_API.USER_ROLES(userId));
}

export function assignUserRoles(userId: number, roleIds: number[]) {
  return put<UserRoleInfo[]>(SYSTEM_API.ASSIGN_ROLES(userId), { role_ids: roleIds });
}

// ── 企业信息配置 ─────────────────────────────────────

export interface EnterpriseProfile {
  company_name: string;
  company_address?: string;
  company_phone?: string;
  company_fax?: string;
  company_zipcode?: string;
  company_credit_code?: string;
  company_bank?: string;
  company_bank_account?: string;
  company_type?: string;
  company_founded?: string;
  company_business_term?: string;
  legal_person_name?: string;
  legal_person_gender?: string;
  legal_person_age?: string;
  legal_person_title?: string;
  authorized_rep_name?: string;
  authorized_rep_phone?: string;
  updated_at?: string;
}

export function getEnterpriseProfile() {
  return get<EnterpriseProfile>(SYSTEM_API.ENTERPRISE_GET);
}

export function updateEnterpriseProfile(data: Partial<EnterpriseProfile>) {
  return put<{ id: number; company_name: string }>(SYSTEM_API.ENTERPRISE_UPDATE, data);
}
