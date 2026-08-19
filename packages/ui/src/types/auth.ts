export interface Account {
  id: string;
  login: string;
  full_name: string;
  roles: string[];
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  account: Account;
}

export interface UserCreate {
  login: string;
  password: string;
  last_name: string;
  first_name: string;
  patronymic?: string;
  roles: string[];
}
