import { useState, useEffect } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import {
  Box, Button, Card, CardContent, Typography, Chip, Alert,
  CircularProgress, List, ListItem, ListItemText, ListItemIcon,
  ListItemButton, Divider, Avatar, Paper,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import AddLocationIcon from '@mui/icons-material/AddLocation';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import ChecklistIcon from '@mui/icons-material/Checklist';
import AssignmentIcon from '@mui/icons-material/Assignment';
import GpsFixedIcon from '@mui/icons-material/GpsFixed';
import { workdayApi, worksApi, authApi, getApiErrorMessage } from '../api';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [workday, setWorkday] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [myCount, setMyCount] = useState(0);
  const [gpsSubmitting, setGpsSubmitting] = useState(false);
  const [gpsMsg, setGpsMsg] = useState('');
  const [role, setRole] = useState(null);

  useEffect(() => {
    authApi.me().then((r) => setRole(r.data?.role)).catch(() => {});
  }, []);

  const isShiftRole = role === 'foreman' || role === 'worker';
  const isForeman = role === 'foreman';

  useEffect(() => {
    if (!isShiftRole) {
      setLoading(false);
      return;
    }
    workdayApi.current()
      .then((r) => setWorkday(r.data))
      .catch((err) => {
        if (err.response?.status === 404) setWorkday(null);
        else setError(getApiErrorMessage(err, 'Не удалось загрузить данные смены'));
      })
      .finally(() => setLoading(false));
    worksApi.myAssignments()
      .then((r) => setMyCount((r.data || []).filter((w) => w.status !== 'completed').length))
      .catch(() => {});
  }, []);

  const sendGpsCheck = () => {
    if (!workday) return;
    setGpsSubmitting(true);
    setGpsMsg('');
    if (!navigator.geolocation) { setGpsMsg('Геолокация не поддерживается'); setGpsSubmitting(false); return; }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          await workdayApi.gpsCheckSubmit(workday.id, {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            captured_at: new Date().toISOString(),
          });
          setGpsMsg('GPS отправлен');
        } catch (err) {
          setGpsMsg(getApiErrorMessage(err, 'Ошибка отправки GPS'));
        } finally {
          setGpsSubmitting(false);
        }
      },
      (err) => { setGpsMsg('Не удалось получить GPS: ' + err.message); setGpsSubmitting(false); },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 },
    );
  };

  if (loading || role === null) return <Box sx={{ textAlign: 'center', mt: 8 }}><CircularProgress /></Box>;

  // Не «сменные» роли — отдаём свой дашборд
  if (role === 'project_manager') return <Navigate to="/dashboard/pm" replace />;
  if (role === 'director' || role === 'administrator') return <Navigate to="/dashboard/director" replace />;
  if (role === 'support_manager' || role === 'accountant') return <Navigate to="/reports" replace />;

  // Нет открытой смены
  if (!workday) {
    return (
      <Box sx={{ textAlign: 'center', mt: 4 }}>
        <Paper elevation={0} sx={{ py: 6, px: 3, bgcolor: 'grey.50', mb: 3 }}>
          <AccessTimeIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
          <Typography variant="h6" gutterBottom>Смена не начата</Typography>
          <Typography color="text.secondary">
            {isForeman ? 'Начните рабочий день, чтобы фиксировать работы' : 'Бригадир ещё не открыл смену.'}
          </Typography>
        </Paper>
        {isForeman && (
          <Button
            variant="contained"
            size="large"
            startIcon={<PlayArrowIcon />}
            onClick={() => navigate('/clock-in')}
            fullWidth
            sx={{ py: 1.5 }}
          >
            Начать смену
          </Button>
        )}
      </Box>
    );
  }

  // Открытая смена
  const clockIn = new Date(workday.clock_in_at);
  const elapsed = Math.round((Date.now() - clockIn.getTime()) / 60000);
  const hours = Math.floor(elapsed / 60);
  const mins = elapsed % 60;

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Таймер */}
      <Card elevation={2} sx={{ mb: 3, bgcolor: 'primary.main', color: 'white' }}>
        <CardContent sx={{ textAlign: 'center', py: 3 }}>
          <Typography variant="overline">Смена активна</Typography>
          <Typography variant="h3" sx={{ fontWeight: 700, my: 1 }}>
            {hours}:{String(mins).padStart(2, '0')}
          </Typography>
          <Typography variant="body2" sx={{ opacity: 0.8 }}>
            Начало: {clockIn.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
          </Typography>
          <Chip
            label={workday.brigade_name}
            size="small"
            sx={{ mt: 1.5, bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }}
          />
        </CardContent>
      </Card>

      {/* Объекты */}
      {workday.sessions?.length > 0 && (
        <Card elevation={1} sx={{ mb: 3 }}>
          <CardContent sx={{ pb: 0 }}>
            <Typography variant="subtitle1" gutterBottom>Объекты за день</Typography>
          </CardContent>
          <List disablePadding>
            {workday.sessions.map((s, idx) => (
              <Box key={s.id}>
                {idx > 0 && <Divider />}
                <ListItemButton
                  disabled={!!s.departed_at}
                  onClick={() => !s.departed_at && navigate(`/object/${s.id}`)}
                >
                  <ListItemIcon>
                    <Avatar sx={{
                      width: 36, height: 36,
                      bgcolor: s.departed_at ? 'grey.200' : 'success.light',
                    }}>
                      <LocationOnIcon sx={{ fontSize: 20, color: s.departed_at ? 'grey.500' : 'white' }} />
                    </Avatar>
                  </ListItemIcon>
                  <ListItemText
                    primary={s.object_name}
                    secondary={
                      s.departed_at
                        ? `Завершено в ${new Date(s.departed_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`
                        : 'На объекте...'
                    }
                  />
                  {!s.departed_at && <Chip label="Активно" color="success" size="small" />}
                </ListItemButton>
              </Box>
            ))}
          </List>
        </Card>
      )}

      {/* Действия */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {isForeman && (
          <Button variant="contained" startIcon={<AddLocationIcon />} onClick={() => navigate('/objects')} fullWidth>
            Прибыть на объект
          </Button>
        )}
        <Button
          variant={myCount > 0 ? 'contained' : 'outlined'}
          color={myCount > 0 ? 'warning' : 'primary'}
          startIcon={<AssignmentIcon />}
          onClick={() => navigate('/my-assignments')}
          fullWidth
        >
          Мои работы{myCount > 0 ? ` (${myCount})` : ''}
        </Button>
        <Button
          variant="outlined"
          startIcon={<GpsFixedIcon />}
          onClick={sendGpsCheck}
          disabled={gpsSubmitting}
          fullWidth
        >
          {gpsSubmitting ? 'Отправка GPS…' : 'Передать GPS'}
        </Button>
        {gpsMsg && <Typography variant="caption" color="text.secondary">{gpsMsg}</Typography>}
        {isForeman && (
          <Button variant="outlined" startIcon={<ChecklistIcon />} onClick={() => navigate('/equipment')} fullWidth>
            Чек-лист оборудования
          </Button>
        )}
        {isForeman && (
          <Button variant="outlined" color="error" startIcon={<StopIcon />} onClick={() => navigate('/clock-out')} fullWidth>
            Завершить смену
          </Button>
        )}
      </Box>
    </Box>
  );
}
