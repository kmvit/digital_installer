import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Typography, Alert, Card, CardContent, CardActionArea,
  CircularProgress, Chip, Avatar,
} from '@mui/material';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import PhotoCapture from '../components/PhotoCapture';
import GpsStatus, { useGps } from '../components/GpsStatus';
import { mobileApi, workdayApi, authApi, getApiErrorMessage } from '../api';

export default function ObjectSelectPage() {
  const navigate = useNavigate();
  const { position, error: gpsError, loading: gpsLoading } = useGps();
  const [objects, setObjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [photo, setPhoto] = useState(null);
  const [photoMeta, setPhotoMeta] = useState(null);
  const handlePhoto = (file, meta) => { setPhoto(file); setPhotoMeta(meta || null); };
  const [arriving, setArriving] = useState(false);
  const [error, setError] = useState('');
  const [workdayId, setWorkdayId] = useState(null);
  const [forbidden, setForbidden] = useState(false);

  useEffect(() => {
    authApi.me()
      .then((r) => {
        if (!['foreman', 'administrator', 'director'].includes(r.data?.role)) {
          setForbidden(true);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    Promise.all([mobileApi.myObjects(), workdayApi.current()])
      .then(([objRes, wdRes]) => {
        setObjects(objRes.data?.results || objRes.data || []);
        setWorkdayId(wdRes.data.id);
      })
      .catch((err) => setError(getApiErrorMessage(err, 'Не удалось загрузить объекты и смену')))
      .finally(() => setLoading(false));
  }, []);

  const handleArrive = async () => {
    if (!selected || !photo) return;
    setArriving(true);
    setError('');
    const formData = new FormData();
    formData.append('project_object', selected.id);
    formData.append('photo', photo);
    if (photoMeta?.captured_at) formData.append('captured_at', photoMeta.captured_at);
    const lat = photoMeta?.latitude ?? position?.latitude;
    const lng = photoMeta?.longitude ?? position?.longitude;
    if (lat != null) formData.append('latitude', lat);
    if (lng != null) formData.append('longitude', lng);
    try {
      const { data } = await workdayApi.arrive(workdayId, formData);
      navigate(`/object/${data.id}`);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Ошибка при отметке прибытия'));
    } finally {
      setArriving(false);
    }
  };

  if (forbidden) {
    return (
      <Box>
        <Typography variant="h5" gutterBottom>Прибытие на объект</Typography>
        <Alert severity="warning">
          Отметку прибытия делает бригадир. Дождитесь, пока он откроет смену на объекте — вам придёт уведомление.
        </Alert>
      </Box>
    );
  }

  if (loading) return <Box sx={{ textAlign: 'center', mt: 8 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Выбор объекта</Typography>
      <Box sx={{ mb: 2 }}>
        <GpsStatus position={position} error={gpsError} loading={gpsLoading} />
      </Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {!selected ? (
        <Box>
          {objects.map((obj) => (
            <Card key={obj.id} elevation={1} sx={{ mb: 1.5 }}>
              <CardActionArea onClick={() => setSelected(obj)} sx={{ p: 2, display: 'flex', justifyContent: 'flex-start' }}>
                <Avatar sx={{ bgcolor: 'primary.light', mr: 2 }}>
                  <LocationOnIcon />
                </Avatar>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle1">
                    {[obj.city_name, obj.address].filter(Boolean).join(', ') || '—'}
                  </Typography>
                  {obj.name && (
                    <Typography variant="body2" color="text.secondary">{obj.name}</Typography>
                  )}
                  {obj.current_stage_name && <Chip label={obj.current_stage_name} size="small" sx={{ mt: 0.5 }} />}
                </Box>
              </CardActionArea>
            </Card>
          ))}
          {objects.length === 0 && (
            <Typography color="text.secondary" align="center" sx={{ mt: 6 }}>Нет доступных объектов</Typography>
          )}
        </Box>
      ) : (
        <Box>
          <Card elevation={2} sx={{ mb: 2, borderLeft: 4, borderColor: 'primary.main' }}>
            <CardContent>
              <Typography variant="h6">
                {[selected.city_name, selected.address].filter(Boolean).join(', ') || '—'}
              </Typography>
              {selected.name && (
                <Typography variant="body2" color="text.secondary">{selected.name}</Typography>
              )}
            </CardContent>
          </Card>
          <Card elevation={1} sx={{ mb: 2 }}>
            <CardContent>
              <PhotoCapture onPhoto={handlePhoto} label="Фото прибытия" required />
            </CardContent>
          </Card>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button variant="outlined" onClick={() => { setSelected(null); setPhoto(null); }} sx={{ flex: 1 }}>Назад</Button>
            <Button variant="contained" onClick={handleArrive} disabled={arriving || !photo} sx={{ flex: 2 }}>
              {arriving ? <CircularProgress size={24} /> : 'Прибыл на объект'}
            </Button>
          </Box>
        </Box>
      )}
    </Box>
  );
}
