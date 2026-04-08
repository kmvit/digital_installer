import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box, Button, Typography, Alert, CircularProgress,
} from '@mui/material';
import PhotoCapture from '../components/PhotoCapture';
import GpsStatus, { useGps } from '../components/GpsStatus';
import { workdayApi } from '../api';

export default function DepartPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { position, error: gpsError, loading: gpsLoading } = useGps();
  const [photo, setPhoto] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [workdayId, setWorkdayId] = useState(null);

  useEffect(() => {
    workdayApi.current()
      .then((r) => setWorkdayId(r.data.id))
      .catch(() => setError('Нет открытой смены'));
  }, []);

  const handleDepart = async () => {
    if (!photo) { setError('Фото обязательно'); return; }
    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('photo', photo);
    if (position) {
      formData.append('latitude', position.latitude);
      formData.append('longitude', position.longitude);
    }

    try {
      await workdayApi.depart(workdayId, formData);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Убытие с объекта</Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Box sx={{ mb: 2 }}>
        <GpsStatus position={position} error={gpsError} loading={gpsLoading} />
      </Box>

      <PhotoCapture onPhoto={setPhoto} label="Фото при убытии" required />

      <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
        <Button variant="outlined" onClick={() => navigate(-1)} sx={{ flex: 1 }}>
          Назад
        </Button>
        <Button
          variant="contained"
          color="error"
          onClick={handleDepart}
          disabled={loading || !photo}
          sx={{ flex: 2 }}
        >
          {loading ? <CircularProgress size={24} /> : 'Покинуть объект'}
        </Button>
      </Box>
    </Box>
  );
}
