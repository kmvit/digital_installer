import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box, Button, Typography, Alert, CircularProgress,
} from '@mui/material';
import PhotoCapture from '../components/PhotoCapture';
import GpsStatus, { useGps } from '../components/GpsStatus';
import { workdayApi, getApiErrorMessage } from '../api';

export default function DepartPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { position, error: gpsError, loading: gpsLoading } = useGps();
  const [photo, setPhoto] = useState(null);
  const [photoMeta, setPhotoMeta] = useState(null);
  const handlePhoto = (file, meta) => { setPhoto(file); setPhotoMeta(meta || null); };
  const [schemePhoto, setSchemePhoto] = useState(null);
  const handleSchemePhoto = (file) => setSchemePhoto(file);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [workdayId, setWorkdayId] = useState(null);

  useEffect(() => {
    workdayApi.current()
      .then((r) => setWorkdayId(r.data.id))
      .catch((err) => setError(getApiErrorMessage(err, 'Нет открытой смены')));
  }, []);

  const handleDepart = async () => {
    if (!photo) { setError('Фото убытия обязательно'); return; }
    if (!schemePhoto) { setError('Загрузите фото схемы выполненных работ'); return; }
    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('photo', photo);
    formData.append('scheme_photo', schemePhoto);
    if (photoMeta?.captured_at) formData.append('captured_at', photoMeta.captured_at);
    const lat = photoMeta?.latitude ?? position?.latitude;
    const lng = photoMeta?.longitude ?? position?.longitude;
    if (lat != null) formData.append('latitude', lat);
    if (lng != null) formData.append('longitude', lng);

    try {
      await workdayApi.depart(workdayId, formData);
      navigate('/');
    } catch (err) {
      setError(getApiErrorMessage(err, 'Ошибка при отметке убытия'));
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

      <PhotoCapture onPhoto={handlePhoto} label="Фото при убытии" required inputId="depart-photo" />

      <Box sx={{ mt: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Схема выполненных работ (фото рукописной схемы)
        </Typography>
        <PhotoCapture onPhoto={handleSchemePhoto} label="Фото схемы работ" required inputId="depart-scheme" />
      </Box>

      <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
        <Button variant="outlined" onClick={() => navigate(-1)} sx={{ flex: 1 }}>
          Назад
        </Button>
        <Button
          variant="contained"
          color="error"
          onClick={handleDepart}
          disabled={loading || !photo || !schemePhoto}
          sx={{ flex: 2 }}
        >
          {loading ? <CircularProgress size={24} /> : 'Покинуть объект'}
        </Button>
      </Box>
    </Box>
  );
}
