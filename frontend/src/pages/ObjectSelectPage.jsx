import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Typography, Alert, Card, CardContent, CardActionArea,
  CircularProgress, Chip, Avatar,
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
    Promise.all([mobileApi.myObjects(), workdayApi.current()])
      .then(([objRes, wdRes]) => {
        setObjects(objRes.data?.results || objRes.data || []);
        setWorkdayId(wdRes.data.id);
      })
      .catch(() => setError('Ошибка загрузки'))
      .finally(() => setLoading(false));
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
      if (data.proximity?.warning) alert(data.proximity.warning);
      navigate(`/object/${data.id}`);
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка');
    } finally {
      setArriving(false);
    }
  };

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
                <Box>
                  <Typography variant="subtitle1">{obj.name}</Typography>
                  <Typography variant="body2" color="text.secondary">{obj.address}</Typography>
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
              <Typography variant="h6">{selected.name}</Typography>
              <Typography variant="body2" color="text.secondary">{selected.address}</Typography>
            </CardContent>
          </Card>
          <Card elevation={1} sx={{ mb: 2 }}>
            <CardContent>
              <PhotoCapture onPhoto={setPhoto} label="Фото прибытия" required />
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
