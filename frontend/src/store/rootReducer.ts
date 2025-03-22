import { combineReducers } from '@reduxjs/toolkit';
import { apiService } from '../services/api/apiService';
import authReducer from '../features/auth/authSlice';
import productsReducer from '../features/products/productsSlice';
import alertsReducer from '../features/alerts/alertsSlice';
import analyticsReducer from '../features/analytics/analyticsSlice';
import profileReducer from '../features/profile/profileSlice';
import uiReducer from '../features/ui/uiSlice';

const rootReducer = combineReducers({
  [apiService.reducerPath]: apiService.reducer,
  auth: authReducer,
  products: productsReducer,
  alerts: alertsReducer,
  analytics: analyticsReducer,
  profile: profileReducer,
  ui: uiReducer,
});

export type RootState = ReturnType<typeof rootReducer>;
export default rootReducer;