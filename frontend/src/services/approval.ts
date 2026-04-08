import { get, post } from '@/utils/request';
import { APPROVAL_API } from '@/constants/api';

export function submitApproval(data: { title: string; biz_type: string; biz_id?: number; approver_id: number }) {
  return post<ApprovalInstance>(APPROVAL_API.SUBMIT, data);
}

export function getMyPending(params?: Record<string, unknown>) {
  return get<PaginatedData<ApprovalInstance>>(APPROVAL_API.MY_PENDING, params);
}

export function getMyInitiated(params?: Record<string, unknown>) {
  return get<PaginatedData<ApprovalInstance>>(APPROVAL_API.MY_INITIATED, params);
}

export function getApprovalDetail(id: number) {
  return get<ApprovalDetail>(APPROVAL_API.DETAIL(id));
}

export function approveInstance(id: number, comment?: string) {
  return post<ApprovalInstance>(APPROVAL_API.APPROVE(id), { comment });
}

export function rejectInstance(id: number, comment?: string) {
  return post<ApprovalInstance>(APPROVAL_API.REJECT(id), { comment });
}

export function transferInstance(id: number, toUserId: number, comment?: string) {
  return post<ApprovalInstance>(APPROVAL_API.TRANSFER(id), { to_user_id: toUserId, comment });
}
