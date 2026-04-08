import { useState, useEffect, useMemo } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar, Toolbar, Typography, BottomNavigation, BottomNavigationAction,
  Box, IconButton,
} from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import WorkIcon from '@mui/icons-material/Engineering';
import HistoryIcon from '@mui/icons-material/History';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import LogoutIcon from '@mui/icons-material/Logout';
import { authApi } from '../api';

const APPROVER_ROLES = ['administrator', 'director', 'project_manager'];

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(null);

  useEffect(() => {
    authApi.me().then((r) => setUser(r.data)).catch(() => {});
  }, []);

  const navItems = useMemo(() => {
    const items = [
      { label: 'Главная', icon: <HomeIcon />, path: '/' },
      { label: 'Смена', icon: <WorkIcon />, path: '/clock-in' },
      { label: 'История', icon: <HistoryIcon />, path: '/history' },
    ];
    if (user && APPROVER_ROLES.includes(user.role)) {
      items.push({ label: 'Приёмка', icon: <CheckCircleIcon />, path: '/approval' });
    }
    return items;
  }, [user]);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    navigate('/login');
  };

  const currentNav = navItems.findIndex((n) => location.pathname === n.path);

  return (
    <Box sx={{ pb: 8, minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="sticky" elevation={1}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Монтажник
          </Typography>
          {user && (
            <Typography variant="body2" sx={{ mr: 1 }}>
              {user.first_name || user.username}
            </Typography>
          )}
          <IconButton color="inherit" onClick={handleLogout} size="small">
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Box sx={{ p: 2, maxWidth: 600, mx: 'auto' }}>
        <Outlet />
      </Box>

      <BottomNavigation
        value={currentNav >= 0 ? currentNav : false}
        onChange={(_, idx) => navigate(navItems[idx].path)}
        showLabels
        sx={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          borderTop: '1px solid #e0e0e0',
          zIndex: 1100,
        }}
      >
        {navItems.map((item) => (
          <BottomNavigationAction
            key={item.path}
            label={item.label}
            icon={item.icon}
          />
        ))}
      </BottomNavigation>
    </Box>
  );
}
