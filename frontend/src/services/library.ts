import { get, post, put, del } from '@/utils/request';
import { LIBRARY_API } from '@/constants/api';

// ========== 资质证书 ==========

export function getQualificationList(params?: Record<string, unknown>) {
  return get<PaginatedData<Qualification>>(LIBRARY_API.QUAL_LIST, params);
}

export function createQualification(data: Partial<Qualification>) {
  return post<Qualification>(LIBRARY_API.QUAL_CREATE, data);
}

export function updateQualification(id: number, data: Partial<Qualification>) {
  return put<Qualification>(LIBRARY_API.QUAL_UPDATE(id), data);
}

export function deleteQualification(id: number) {
  return del(LIBRARY_API.QUAL_DELETE(id));
}

// ========== 业绩案例 ==========

export function getAchievementList(params?: Record<string, unknown>) {
  return get<PaginatedData<Achievement>>(LIBRARY_API.ACHV_LIST, params);
}

export function createAchievement(data: Partial<Achievement>) {
  return post<Achievement>(LIBRARY_API.ACHV_CREATE, data);
}

export function updateAchievement(id: number, data: Partial<Achievement>) {
  return put<Achievement>(LIBRARY_API.ACHV_UPDATE(id), data);
}

export function deleteAchievement(id: number) {
  return del(LIBRARY_API.ACHV_DELETE(id));
}

// ========== 人员证书 ==========

export function getPersonnelCertList(params?: Record<string, unknown>) {
  return get<PaginatedData<PersonnelCert>>(LIBRARY_API.PCERT_LIST, params);
}

export function createPersonnelCert(data: Partial<PersonnelCert>) {
  return post<PersonnelCert>(LIBRARY_API.PCERT_CREATE, data);
}

export function updatePersonnelCert(id: number, data: Partial<PersonnelCert>) {
  return put<PersonnelCert>(LIBRARY_API.PCERT_UPDATE(id), data);
}

export function deletePersonnelCert(id: number) {
  return del(LIBRARY_API.PCERT_DELETE(id));
}

// ========== 产品/设备 ==========

export function getProductList(params?: Record<string, unknown>) {
  return get<PaginatedData<Product>>(LIBRARY_API.PROD_LIST, params);
}

export function createProduct(data: Partial<Product>) {
  return post<Product>(LIBRARY_API.PROD_CREATE, data);
}

export function updateProduct(id: number, data: Partial<Product>) {
  return put<Product>(LIBRARY_API.PROD_UPDATE(id), data);
}

export function deleteProduct(id: number) {
  return del(LIBRARY_API.PROD_DELETE(id));
}
