import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Typography, Alert, Checkbox, FormControlLabel,
  List, ListItem, CircularProgress, Card, CardContent, Chip,
} from '@mui/material';
import GroupsIcon from '@mui/icons-material/Groups';
import PhotoCapture from '../components/PhotoCapture';
import GpsStatus, { useGps } from '../components/GpsStatus';
import { workdayApi, mobileApi, getApiErrorMessage } from '../api';

export default function ClockInPage() {
  const navigate = useNavigate();
  const { position, error: gpsError, loading: gpsLoading } = useGps();
  const [photo, setPhoto] = useState(null);
  const [members, setMembers] = useState([]);
  const [selected, setSelected] = useState([]);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [currentWorkday, setCurrentWorkday] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        const currentResp = await workdayApi.current();
        setCurrentWorkday(currentResp.data);
      } catch (err) {
        if (err.response?.status !== 404) {
          setError(getApiErrorMessage(err, 'Не удалось загрузить данные смены'));
        }
      }

      try {
        const brigadeResp = await mobileApi.myBrigade();
        setMembers(brigadeResp.data.members || []);
      } catch (err) {
        setError((prev) => prev || getApiErrorMessage(err, 'Не удалось загрузить состав бригады'));
      } finally {
        setInitialLoading(false);
      }
    };

    loadData();
  }, []);

  const toggleMember = (id) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleSubmit = async () => {
    if (!photo) { setError('Фото обязательно для начала смены'); return; }
    setLoading(true);
    setError('');
    const formData = new FormData();
    formData.append('photo', photo);
    if (position) {
      formData.append('latitude', position.latitude);
      formData.append('longitude', position.longitude);
    }
    selected.forEach((id) => formData.append('workers_present', id));
    try {
      await workdayApi.clockIn(formData);
      navigate('/');
    } catch (err) {
      setError(getApiErrorMessage(err, 'Ошибка при открытии смены'));
    } finally {
      setLoading(false);
    }
  };

  if (initialLoading) {
    return <Box sx={{ textAlign: 'center', mt: 8 }}><CircularProgress /></Box>;
  }

  if (currentWorkday) {
    const clockIn = new Date(currentWorkday.clock_in_at);
    return (
      <Box>
        <Typography variant="h5" gutterBottom>Смена</Typography>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <Card elevation={1} sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>Текущая смена</Typography>
            <Typography variant="h6" sx={{ mb: 1 }}>Смена уже открыта</Typography>
            <Typography variant="body2" color="text.secondary">
              Начало: {clockIn.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
            </Typography>
            <Chip label={currentWorkday.brigade_name} size="small" color="primary" sx={{ mt: 1.5 }} />
          </CardContent>
        </Card>

        <Button variant="contained" fullWidth sx={{ mb: 1.5 }} onClick={() => navigate('/')}>
          Перейти на главную
        </Button>
        <Button variant="outlined" color="error" fullWidth onClick={() => navigate('/clock-out')}>
          Завершить смену
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Начало смены</Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Card elevation={1} sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>GPS</Typography>
          <GpsStatus position={position} error={gpsError} loading={gpsLoading} />
        </CardContent>
      </Card>

      <Card elevation={1} sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>Фото бригады</Typography>
          <PhotoCapture onPhoto={setPhoto} label="Сделать фото бригады" required />
        </CardContent>
      </Card>

      {members.length > 0 && (
        <Card elevation={1} sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <GroupsIcon color="primary" />
              <Typography variant="subtitle1">Присутствующие</Typography>
            </Box>
            <List disablePadding>
              {members.map((m) => (
                <ListItem key={m.id} disablePadding sx={{ py: 0.5 }}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={selected.includes(m.id)}
                        onChange={() => toggleMember(m.id)}
                      />
                    }
                    label={m.first_name && m.last_name ? `${m.last_name} ${m.first_name}` : m.username}
                  />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      <Button variant="contained" size="large" fullWidth onClick={handleSubmit} disabled={loading || !photo}>
        {loading ? <CircularProgress size={24} /> : 'Начать смену'}
      </Button>
    </Box>
  );
}
