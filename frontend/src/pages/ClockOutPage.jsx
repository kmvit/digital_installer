import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Typography, Alert, CircularProgress,
  Card, CardContent, List, ListItem, ListItemText, Chip,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HighlightOffIcon from '@mui/icons-material/HighlightOff';
import PhotoCapture from '../components/PhotoCapture';
import GpsStatus, { useGps } from '../components/GpsStatus';
import { workdayApi, getApiErrorMessage } from '../api';

export default function ClockOutPage() {
  const navigate = useNavigate();
  const { position, error: gpsError, loading: gpsLoading } = useGps();
  const [photo, setPhoto] = useState(null);
  const [photoMeta, setPhotoMeta] = useState(null);
  const handlePhoto = (file, meta) => { setPhoto(file); setPhotoMeta(meta || null); };
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [workdayId, setWorkdayId] = useState(null);
  const [gpsList, setGpsList] = useState([]);

  const reloadGps = (id) => {
    workdayApi.gpsCheckList(id)
      .then((r) => setGpsList(r.data || []))
      .catch(() => {});
  };

  useEffect(() => {
    workdayApi.current()
      .then((r) => {
        setWorkdayId(r.data.id);
        reloadGps(r.data.id);
      })
      .catch((err) => setError(getApiErrorMessage(err, 'Нет открытой смены')));
  }, []);

  const handleClockOut = async () => {
    if (!photo) { setError('Фото обязательно'); return; }
    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('photo', photo);
    if (photoMeta?.captured_at) formData.append('captured_at', photoMeta.captured_at);
    const lat = photoMeta?.latitude ?? position?.latitude;
    const lng = photoMeta?.longitude ?? position?.longitude;
    if (lat != null) formData.append('latitude', lat);
    if (lng != null) formData.append('longitude', lng);

    try {
      const { data } = await workdayApi.clockOut(formData);
      navigate(`/summary/${data.id}`);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Ошибка при завершении смены'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Завершение смены</Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Box sx={{ mb: 2 }}>
        <GpsStatus position={position} error={gpsError} loading={gpsLoading} />
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Все незакрытые сессии на объектах будут закрыты автоматически.
      </Typography>

      <Button
        variant="outlined"
        fullWidth
        sx={{ mb: 2 }}
        onClick={() => navigate('/equipment?type=evening')}
      >
        Заполнить вечерний чек-лист оборудования
      </Button>

      <Card elevation={1} sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>GPS-проверка членов бригады</Typography>
          {gpsList.length === 0 ? (
            <Typography variant="caption" color="text.secondary">Нет данных о составе бригады</Typography>
          ) : (
            <List dense disablePadding>
              {gpsList.map((m) => (
                <ListItem key={m.id} disableGutters>
                  {m.checked
                    ? <CheckCircleIcon color="success" sx={{ mr: 1 }} />
                    : <HighlightOffIcon color="warning" sx={{ mr: 1 }} />}
                  <ListItemText
                    primary={m.name}
                    secondary={m.checked
                      ? new Date(m.captured_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
                      : 'GPS не передан'}
                  />
                  {m.checked && <Chip label="OK" size="small" color="success" />}
                </ListItem>
              ))}
            </List>
          )}
          <Button size="small" sx={{ mt: 1 }} onClick={() => workdayId && reloadGps(workdayId)}>Обновить</Button>
        </CardContent>
      </Card>

      <PhotoCapture onPhoto={handlePhoto} label="Фото завершения смены" required />

      <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
        <Button variant="outlined" onClick={() => navigate('/')} sx={{ flex: 1 }}>
          Назад
        </Button>
        <Button
          variant="contained"
          color="error"
          onClick={handleClockOut}
          disabled={loading || !photo}
          sx={{ flex: 2 }}
        >
          {loading ? <CircularProgress size={24} /> : 'Завершить смену'}
        </Button>
      </Box>
    </Box>
  );
}
