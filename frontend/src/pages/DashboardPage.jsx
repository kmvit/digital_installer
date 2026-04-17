import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
import { workdayApi } from '../api';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [workday, setWorkday] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    workdayApi.current()
      .then((r) => setWorkday(r.data))
      .catch((err) => {
        if (err.response?.status === 404) setWorkday(null);
        else setError('Ошибка загрузки');
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Box sx={{ textAlign: 'center', mt: 8 }}><CircularProgress /></Box>;

  // Нет открытой смены
  if (!workday) {
    return (
      <Box sx={{ textAlign: 'center', mt: 4 }}>
        <Paper elevation={0} sx={{ py: 6, px: 3, bgcolor: 'grey.50', mb: 3 }}>
          <AccessTimeIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
          <Typography variant="h6" gutterBottom>Смена не начата</Typography>
          <Typography color="text.secondary">
            Начните рабочий день, чтобы фиксировать работы
          </Typography>
        </Paper>
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
        <Button variant="contained" startIcon={<AddLocationIcon />} onClick={() => navigate('/objects')} fullWidth>
          Прибыть на объект
        </Button>
        <Button variant="outlined" startIcon={<ChecklistIcon />} onClick={() => navigate('/equipment')} fullWidth>
          Чек-лист оборудования
        </Button>
        <Button variant="outlined" color="error" startIcon={<StopIcon />} onClick={() => navigate('/clock-out')} fullWidth>
          Завершить смену
        </Button>
      </Box>
    </Box>
  );
}
