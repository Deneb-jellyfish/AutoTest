import { request } from './request';
import type { LoginData, UserInfo } from './types';

export function fetchLogin(usernameOrEmail: string, password: string) {
  return request<LoginData>({
    url: '/users/login',
    method: 'post',
    data: { usernameOrEmail, password }
  });
}

export function fetchGetVerificationCode(email: string) {
  return request<null>({
    url: '/users/verification-codes',
    method: 'post',
    params: { email }
  });
}

export function fetchRegister(
  username: string,
  password: string,
  email: string,
  verificationCode: string
) {
  return request<UserInfo>({
    url: '/users',
    method: 'post',
    data: { username, password, email, verificationCode }
  });
}

export function fetchResetPassword(email: string, verificationCode: string, newPassword: string) {
  return request<null>({
    url: '/users/password',
    method: 'put',
    data: { email, verificationCode, newPassword }
  });
}

export function fetchUpdateProfile(payload: {
  name?: string;
  phone?: string;
  website?: string;
}) {
  return request<UserInfo>({
    url: '/users/me',
    method: 'put',
    data: payload
  });
}
