import { useCallback } from 'react';
import { useAppDispatch } from './';
import { showNotification, hideNotification, removeNotification } from '../features/ui/uiSlice';

// Hook pour gérer les notifications
export const useNotifications = () => {
  const dispatch = useAppDispatch();

  const notify = useCallback(
    (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'info') => {
      dispatch(showNotification({ message, type }));
    },
    [dispatch]
  );

  const success = useCallback(
    (message: string) => notify(message, 'success'),
    [notify]
  );

  const error = useCallback(
    (message: string) => notify(message, 'error'),
    [notify]
  );

  const info = useCallback(
    (message: string) => notify(message, 'info'),
    [notify]
  );

  const warning = useCallback(
    (message: string) => notify(message, 'warning'),
    [notify]
  );

  const hide = useCallback(
    (id: number) => dispatch(hideNotification(id)),
    [dispatch]
  );

  const remove = useCallback(
    (id: number) => dispatch(removeNotification(id)),
    [dispatch]
  );

  return {
    notify,
    success,
    error,
    info,
    warning,
    hide,
    remove,
  };
};