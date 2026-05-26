export interface ApiResult<T> {
  code: number;
  msg: string;
  data: T;
}

export interface UserInfo {
  id: number;
  username: string;
  email: string;
  name?: string;
  phone?: string;
  website?: string;
}

export interface LoginData {
  token: string;
  user: UserInfo;
}
