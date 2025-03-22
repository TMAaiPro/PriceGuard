import { useDispatch } from 'react-redux';
import type { AppDispatch } from '../store/store';

// Hook personnalisé pour utiliser le dispatch avec les types corrects
export const useAppDispatch = () => useDispatch<AppDispatch>();