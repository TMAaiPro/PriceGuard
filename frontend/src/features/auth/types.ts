export interface User {
  id: number;
  username: string;
  email: string;
  avatar?: string;
  notification_email: boolean;
  notification_push: boolean;
  premium_until?: string;
  is_premium: boolean;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
}

export interface AuthResponse {
  user: User;
  token: string;
  refresh_token: string;
}