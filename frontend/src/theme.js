import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#9c27b0',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    // Всё крупнее на 20-30%
    h3: { fontSize: '2.4rem', fontWeight: 700 },
    h4: { fontSize: '2rem', fontWeight: 700 },
    h5: { fontSize: '1.6rem', fontWeight: 700 },
    h6: { fontSize: '1.35rem', fontWeight: 700 },
    subtitle1: { fontSize: '1.15rem', fontWeight: 600 },
    subtitle2: { fontSize: '1.05rem', fontWeight: 600 },
    body1: { fontSize: '1.05rem' },
    body2: { fontSize: '0.95rem' },
    button: { fontSize: '1.1rem', fontWeight: 600 },
    caption: { fontSize: '0.85rem' },
  },
  shape: {
    borderRadius: 14,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          minHeight: 56,
          textTransform: 'none',
          fontWeight: 700,
          fontSize: '1.1rem',
          padding: '12px 24px',
        },
        sizeSmall: {
          minHeight: 44,
          fontSize: '1rem',
          padding: '8px 16px',
        },
        sizeLarge: {
          minHeight: 64,
          fontSize: '1.2rem',
          padding: '16px 32px',
        },
      },
    },
    MuiFab: {
      styleOverrides: {
        root: {
          width: 72,
          height: 72,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontSize: '0.9rem',
          height: 36,
        },
        sizeSmall: {
          fontSize: '0.85rem',
          height: 30,
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        size: 'medium',
      },
      styleOverrides: {
        root: {
          '& .MuiInputBase-input': {
            fontSize: '1.1rem',
            padding: '16px 14px',
          },
          '& .MuiInputLabel-root': {
            fontSize: '1.05rem',
          },
        },
      },
    },
    MuiCheckbox: {
      styleOverrides: {
        root: {
          padding: 12,
          '& .MuiSvgIcon-root': {
            fontSize: 30,
          },
        },
      },
    },
    MuiFormControlLabel: {
      styleOverrides: {
        label: {
          fontSize: '1.05rem',
        },
      },
    },
    MuiListItemText: {
      styleOverrides: {
        primary: {
          fontSize: '1.05rem',
          fontWeight: 500,
        },
        secondary: {
          fontSize: '0.9rem',
        },
      },
    },
    MuiBottomNavigationAction: {
      styleOverrides: {
        root: {
          minWidth: 60,
          '& .MuiSvgIcon-root': {
            fontSize: 28,
          },
        },
        label: {
          fontSize: '0.8rem',
          '&.Mui-selected': {
            fontSize: '0.85rem',
          },
        },
      },
    },
    MuiBottomNavigation: {
      styleOverrides: {
        root: {
          height: 68,
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          fontSize: '1rem',
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          padding: 12,
        },
      },
    },
    MuiToggleButton: {
      styleOverrides: {
        root: {
          fontSize: '0.95rem',
          padding: '10px 16px',
        },
      },
    },
    MuiCardContent: {
      styleOverrides: {
        root: {
          padding: 20,
          '&:last-child': {
            paddingBottom: 20,
          },
        },
      },
    },
    MuiAvatar: {
      styleOverrides: {
        root: {
          width: 44,
          height: 44,
          fontSize: '1.1rem',
        },
      },
    },
    MuiDialogTitle: {
      styleOverrides: {
        root: {
          fontSize: '1.3rem',
        },
      },
    },
  },
});

export default theme;
