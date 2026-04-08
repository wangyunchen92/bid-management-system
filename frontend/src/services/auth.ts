import { get, post, put } from '@/utils/request';
import { AUTH_API } from '@/constants/api';

export function login(params: LoginParams) {
  return post<LoginResult>(AUTH_API.LOGIN, params);
}

export function logout() {
  return post(AUTH_API.LOGOUT);
}

export function refreshToken(refresh_token: string) {
  return post<LoginResult>(AUTH_API.REFRESH, { refresh_token });
}

export function getCurrentUser() {
  return get<CurrentUser>(AUTH_API.ME);
}

export function changePassword(data: { old_password: string; new_password: string }) {
  return put(AUTH_API.CHANGE_PASSWORD, data);
}
