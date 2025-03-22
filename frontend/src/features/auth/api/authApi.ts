import { apiService } from '../../../services/api/apiService';
import { LoginRequest, RegisterRequest, AuthResponse } from '../types';

// Extension de l'API service pour les endpoints d'authentification
export const authApi = apiService.injectEndpoints({
  endpoints: (builder) => ({
    login: builder.mutation<AuthResponse, LoginRequest>({
      query: (credentials) => ({
        url: '/users/login/',
        method: 'POST',
        body: credentials,
      }),
    }),
    register: builder.mutation<AuthResponse, RegisterRequest>({
      query: (userData) => ({
        url: '/users/create/',
        method: 'POST',
        body: userData,
      }),
    }),
    refreshToken: builder.mutation<{ access: string }, { refresh: string }>({
      query: (refreshToken) => ({
        url: '/token/refresh/',
        method: 'POST',
        body: refreshToken,
      }),
    }),
    logout: builder.mutation<void, void>({
      query: () => ({
        url: '/users/logout/',
        method: 'POST',
      }),
    }),
    getUser: builder.query<User, void>({
      query: () => '/users/me/',
      providesTags: ['User'],
    }),
  }),
});

export const {
  useLoginMutation,
  useRegisterMutation,
  useRefreshTokenMutation,
  useLogoutMutation,
  useGetUserQuery,
} = authApi;