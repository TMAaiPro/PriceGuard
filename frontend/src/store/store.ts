import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';
import { 
  persistStore, 
  persistReducer,
  FLUSH,
  REHYDRATE,
  PAUSE,
  PERSIST,
  PURGE,
  REGISTER,
} from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import rootReducer, { RootState } from './rootReducer';
import { apiService } from '../services/api/apiService';

// Configuration pour redux-persist
const persistConfig = {
  key: 'root',
  storage,
  whitelist: ['auth'], // Nous voulons persister uniquement l'authentification
};

// Créer un reducer persistant
const persistedReducer = persistReducer(persistConfig, rootReducer);

// Configuration du store
export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER],
      },
    }).concat(apiService.middleware),
  devTools: process.env.NODE_ENV !== 'production',
});

// Persistor pour redux-persist
export const persistor = persistStore(store);

// Setup listeners pour RTK Query
setupListeners(store.dispatch);

// Types
export type AppDispatch = typeof store.dispatch;
export { RootState };