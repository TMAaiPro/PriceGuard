import { useSelector, TypedUseSelectorHook } from 'react-redux';
import type { RootState } from '../store/store';

// Hook personnalisé pour utiliser le selector avec les types corrects
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;