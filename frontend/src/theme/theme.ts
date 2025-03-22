import { createTheme, responsiveFontSizes } from '@mui/material/styles';
import { palette } from './palette';
import { typography } from './typography';
import { components } from './components';

const baseTheme = createTheme({
  palette,
  typography,
  shape: {
    borderRadius: 8,
  },
  spacing: 8,
});

const theme = createTheme(
  {
    ...baseTheme,
    components,
  },
  baseTheme
);

// Rendre les tailles de police responsive
export const responsiveTheme = responsiveFontSizes(theme);

export default responsiveTheme;