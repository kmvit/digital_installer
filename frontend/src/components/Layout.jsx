import { useState, useEffect, useMemo } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar, Toolbar, Typography, BottomNavigation, BottomNavigationAction,
  Box, IconButton, Chip, Snackbar, Alert,
} from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import WorkIcon from '@mui/icons-material/Engineering';
import HistoryIcon from '@mui/icons-material/History';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AssessmentIcon from '@mui/icons-material/Assessment';
import LogoutIcon from '@mui/icons-material/Logout';
import CloudOffIcon from '@mui/icons-material/CloudOff';
import SyncIcon from '@mui/icons-material/Sync';
import { authApi } from '../api';
import useOnlineStatus from '../hooks/useOnlineStatus';

const APPROVER_ROLES = ['administrator', 'director', 'project_manager'];
const REPORT_ROLES = ['administrator', 'director', 'project_manager', 'support_manager', 'accountant'];

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(null);
  const { isOnline, pendingCount, syncing, doSync } = useOnlineStatus();
  const [syncResult, setSyncResult] = useState(null);

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
    if (user && REPORT_ROLES.includes(user.role)) {
      items.push({ label: 'Отчёты', icon: <AssessmentIcon />, path: '/reports' });
    }
    return items;
  }, [user]);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    navigate('/login');
  };

  const handleSync = async () => {
    const result = await doSync();
    if (result) setSyncResult(result);
  };

  const currentNav = navItems.findIndex((n) => location.pathname === n.path);

  return (
    <Box sx={{ pb: 8, minHeight: '100vh', bgcolor: 'grey.50' }}>
      <AppBar position="sticky" elevation={1}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>Монтажник</Typography>

          {!isOnline && (
            <Chip icon={<CloudOffIcon />} label={pendingCount > 0 ? `Офлайн | ${pendingCount}` : 'Офлайн'} size="small" color="warning" sx={{ mr: 1 }} />
          )}
          {isOnline && pendingCount > 0 && (
            <Chip icon={<SyncIcon />} label={`${pendingCount}`} size="small" color="info" onClick={handleSync} sx={{ mr: 1, cursor: 'pointer' }} />
          )}

          {user && (
            <Typography variant="body2" sx={{ mr: 1 }}>{user.first_name || user.username}</Typography>
          )}
          <IconButton color="inherit" onClick={handleLogout} size="small">
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      {!isOnline && (
        <Box sx={{ bgcolor: 'warning.light', px: 2, py: 0.5, textAlign: 'center', fontSize: 13 }}>
          Нет сети. Данные сохраняются локально.
        </Box>
      )}

      <Box sx={{ p: 2, maxWidth: 600, mx: 'auto' }}>
        <Outlet />
      </Box>

      <BottomNavigation
        value={currentNav >= 0 ? currentNav : false}
        onChange={(_, idx) => navigate(navItems[idx].path)}
        showLabels
        sx={{ position: 'fixed', bottom: 0, left: 0, right: 0, borderTop: '1px solid', borderColor: 'divider', zIndex: 1100 }}
      >
        {navItems.map((item) => (
          <BottomNavigationAction key={item.path} label={item.label} icon={item.icon} />
        ))}
      </BottomNavigation>

      <Snackbar open={!!syncResult} autoHideDuration={4000} onClose={() => setSyncResult(null)} anchorOrigin={{ vertical: 'top', horizontal: 'center' }}>
        <Alert severity={syncResult?.failed ? 'warning' : 'success'} onClose={() => setSyncResult(null)}>
          {syncResult?.synced > 0 && `Отправлено: ${syncResult.synced}. `}
          {syncResult?.failed > 0 && `Ошибок: ${syncResult.failed}. `}
          {syncResult?.remaining === 0 && 'Все данные синхронизированы!'}
        </Alert>
      </Snackbar>
    </Box>
  );
}
