import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { RootState } from '../../store/store';

// Base URL de l'API backend
const API_BASE_URL = '/api';

// Configuration de base pour l'API
export const apiService = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({
    baseUrl: API_BASE_URL,
    prepareHeaders: (headers, { getState }) => {
      // Récupérer le token d'authentification depuis le state
      const token = (getState() as RootState).auth.token;
      
      // Si nous avons un token, l'ajouter aux en-têtes de la requête
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
      
      return headers;
    },
  }),
  // Définition des endpoints centraux
  endpoints: () => ({}),
  // Active le cache automatique et le refetching
  tagTypes: ['User', 'Product', 'Alert', 'Analytics', 'Retailer'],
});