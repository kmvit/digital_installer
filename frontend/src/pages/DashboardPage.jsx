import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Card, CardContent, Typography, Chip, Alert,
  CircularProgress, List, ListItem, ListItemText, Divider,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import AddLocationIcon from '@mui/icons-material/AddLocation';
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

  if (loading) return <Box sx={{ textAlign: 'center', mt: 4 }}><CircularProgress /></Box>;

  // Нет открытой смены
  if (!workday) {
    return (
      <Box sx={{ textAlign: 'center', mt: 6 }}>
        <Typography variant="h6" gutterBottom>Смена не начата</Typography>
        <Typography color="text.secondary" sx={{ mb: 4 }}>
          Начните рабочий день, чтобы фиксировать работы
        </Typography>
        <Button
          variant="contained"
          size="large"
          startIcon={<PlayArrowIcon />}
          onClick={() => navigate('/clock-in')}
          sx={{ px: 6, py: 2 }}
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

      <Card sx={{ mb: 2, bgcolor: 'primary.main', color: 'white' }}>
        <CardContent>
          <Typography variant="body2">Смена открыта</Typography>
          <Typography variant="h4">{hours}ч {mins}м</Typography>
          <Typography variant="body2">
            Начало: {clockIn.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
          </Typography>
          <Chip
            label={workday.brigade_name}
            size="small"
            sx={{ mt: 1, bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }}
          />
        </CardContent>
      </Card>

      {/* Открытые сессии */}
      {workday.sessions?.length > 0 && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>Объекты за день</Typography>
            <List disablePadding>
              {workday.sessions.map((s) => (
                <Box key={s.id}>
                  <ListItem
                    disablePadding
                    onClick={() => !s.departed_at && navigate(`/object/${s.id}`)}
                    sx={{ cursor: s.departed_at ? 'default' : 'pointer', py: 1 }}
                  >
                    <ListItemText
                      primary={s.object_name}
                      secondary={
                        s.departed_at
                          ? `Завершено в ${new Date(s.departed_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`
                          : 'На объекте...'
                      }
                    />
                    {!s.departed_at && (
                      <Chip label="Активно" color="success" size="small" />
                    )}
                  </ListItem>
                  <Divider />
                </Box>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      {/* Действия */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Button
          variant="contained"
          startIcon={<AddLocationIcon />}
          onClick={() => navigate('/objects')}
          fullWidth
        >
          Прибыть на объект
        </Button>

        <Button
          variant="outlined"
          onClick={() => navigate('/equipment')}
          fullWidth
        >
          Чек-лист оборудования
        </Button>

        <Button
          variant="contained"
          color="error"
          startIcon={<StopIcon />}
          onClick={() => navigate('/clock-out')}
          fullWidth
        >
          Завершить смену
        </Button>
      </Box>
    </Box>
  );
}
