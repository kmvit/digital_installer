import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Typography, Alert, CircularProgress,
} from '@mui/material';
import PhotoCapture from '../components/PhotoCapture';
import GpsStatus, { useGps } from '../components/GpsStatus';
import { workdayApi, getApiErrorMessage } from '../api';

export default function ClockOutPage() {
  const navigate = useNavigate();
  const { position, error: gpsError, loading: gpsLoading } = useGps();
  const [photo, setPhoto] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [workdayId, setWorkdayId] = useState(null);

  useEffect(() => {
    workdayApi.current()
      .then((r) => setWorkdayId(r.data.id))
      .catch((err) => setError(getApiErrorMessage(err, 'Нет открытой смены')));
  }, []);

  const handleClockOut = async () => {
    if (!photo) { setError('Фото обязательно'); return; }
    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('photo', photo);
    if (position) {
      formData.append('latitude', position.latitude);
      formData.append('longitude', position.longitude);
    }

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

      <PhotoCapture onPhoto={setPhoto} label="Фото завершения смены" required />

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
