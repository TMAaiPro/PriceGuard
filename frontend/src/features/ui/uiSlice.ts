import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface UIState {
  drawerOpen: boolean;
  theme: 'light' | 'dark';
  notifications: {
    message: string;
    type: 'success' | 'error' | 'info' | 'warning';
    open: boolean;
    id: number;
  }[];
}

const initialState: UIState = {
  drawerOpen: false,
  theme: 'light',
  notifications: [],
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleDrawer: (state) => {
      state.drawerOpen = !state.drawerOpen;
    },
    setDrawerOpen: (state, action: PayloadAction<boolean>) => {
      state.drawerOpen = action.payload;
    },
    toggleTheme: (state) => {
      state.theme = state.theme === 'light' ? 'dark' : 'light';
    },
    setTheme: (state, action: PayloadAction<'light' | 'dark'>) => {
      state.theme = action.payload;
    },
    showNotification: (state, action: PayloadAction<{ message: string; type: 'success' | 'error' | 'info' | 'warning' }>) => {
      const id = Date.now();
      state.notifications.push({
        ...action.payload,
        open: true,
        id,
      });
    },
    hideNotification: (state, action: PayloadAction<number>) => {
      const index = state.notifications.findIndex((n) => n.id === action.payload);
      if (index !== -1) {
        state.notifications[index].open = false;
      }
    },
    removeNotification: (state, action: PayloadAction<number>) => {
      state.notifications = state.notifications.filter((n) => n.id !== action.payload);
    },
  },
});

export const {
  toggleDrawer,
  setDrawerOpen,
  toggleTheme,
  setTheme,
  showNotification,
  hideNotification,
  removeNotification,
} = uiSlice.actions;

export default uiSlice.reducer;