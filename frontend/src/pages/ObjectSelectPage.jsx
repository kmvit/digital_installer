import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Typography, Alert, Card, CardContent, CardActionArea,
  CircularProgress, Chip,
} from '@mui/material';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import PhotoCapture from '../components/PhotoCapture';
import GpsStatus, { useGps } from '../components/GpsStatus';
import { mobileApi, workdayApi } from '../api';

export default function ObjectSelectPage() {
  const navigate = useNavigate();
  const { position, error: gpsError, loading: gpsLoading } = useGps();
  const [objects, setObjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [photo, setPhoto] = useState(null);
  const [arriving, setArriving] = useState(false);
  const [error, setError] = useState('');
  const [workdayId, setWorkdayId] = useState(null);

  useEffect(() => {
    Promise.all([
      mobileApi.myObjects(),
      workdayApi.current(),
    ]).then(([objRes, wdRes]) => {
      setObjects(objRes.data?.results || objRes.data || []);
      setWorkdayId(wdRes.data.id);
    }).catch(() => {
      setError('Ошибка загрузки');
    }).finally(() => setLoading(false));
  }, []);

  const handleArrive = async () => {
    if (!selected || !photo) return;
    setArriving(true);
    setError('');

    const formData = new FormData();
    formData.append('project_object', selected.id);
    formData.append('photo', photo);
    if (position) {
      formData.append('latitude', position.latitude);
      formData.append('longitude', position.longitude);
    }

    try {
      const { data } = await workdayApi.arrive(workdayId, formData);
      if (data.proximity?.warning) {
        // Показать предупреждение, но не блокировать
        alert(data.proximity.warning);
      }
      navigate(`/object/${data.id}`);
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка');
    } finally {
      setArriving(false);
    }
  };

  if (loading) return <Box sx={{ textAlign: 'center', mt: 4 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Выбор объекта</Typography>
      <GpsStatus position={position} error={gpsError} loading={gpsLoading} />

      {error && <Alert severity="error" sx={{ mt: 1, mb: 2 }}>{error}</Alert>}

      {!selected ? (
        <Box sx={{ mt: 2 }}>
          {objects.map((obj) => (
            <Card key={obj.id} sx={{ mb: 1 }}>
              <CardActionArea onClick={() => setSelected(obj)} sx={{ p: 2 }}>
                <Typography variant="subtitle1">{obj.name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {obj.address}
                </Typography>
                {obj.current_stage_name && (
                  <Chip label={obj.current_stage_name} size="small" sx={{ mt: 1 }} />
                )}
              </CardActionArea>
            </Card>
          ))}
          {objects.length === 0 && (
            <Typography color="text.secondary" align="center" sx={{ mt: 4 }}>
              Нет доступных объектов
            </Typography>
          )}
        </Box>
      ) : (
        <Box sx={{ mt: 2 }}>
          <Card sx={{ mb: 2, bgcolor: 'primary.50' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <LocationOnIcon color="primary" />
                <Typography variant="h6">{selected.name}</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                {selected.address}
              </Typography>
            </CardContent>
          </Card>

          <PhotoCapture onPhoto={setPhoto} label="Фото прибытия" required />

          <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
            <Button
              variant="outlined"
              onClick={() => { setSelected(null); setPhoto(null); }}
              sx={{ flex: 1 }}
            >
              Назад
            </Button>
            <Button
              variant="contained"
              onClick={handleArrive}
              disabled={arriving || !photo}
              sx={{ flex: 2 }}
            >
              {arriving ? <CircularProgress size={24} /> : 'Прибыл на объект'}
            </Button>
          </Box>
        </Box>
      )}
    </Box>
  );
}
