import { useCallback } from 'react';
import { useAppSelector, useAppDispatch } from './';
import { 
  selectCurrentUser, 
  selectIsAuthenticated, 
  selectAuthError, 
  selectAuthLoading,
  login,
  register,
  logoutAction
} from '../features/auth/authSlice';
import { LoginRequest, RegisterRequest } from '../features/auth/types';

// Hook pour gérer l'authentification
export const useAuth = () => {
  const dispatch = useAppDispatch();
  const user = useAppSelector(selectCurrentUser);
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const error = useAppSelector(selectAuthError);
  const isLoading = useAppSelector(selectAuthLoading);

  const loginUser = useCallback(
    (credentials: LoginRequest) => dispatch(login(credentials)),
    [dispatch]
  );

  const registerUser = useCallback(
    (userData: RegisterRequest) => dispatch(register(userData)),
    [dispatch]
  );

  const logout = useCallback(() => dispatch(logoutAction()), [dispatch]);

  return {
    user,
    isAuthenticated,
    error,
    isLoading,
    login: loginUser,
    register: registerUser,
    logout,
  };
};