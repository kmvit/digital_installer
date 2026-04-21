import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box, Button, Typography, Alert, Card, CardContent, Fab,
  CircularProgress, Chip, Avatar,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import ExitToAppIcon from '@mui/icons-material/ExitToApp';
import BuildIcon from '@mui/icons-material/Build';
import PhotoCameraIcon from '@mui/icons-material/PhotoCamera';
import { worksApi, getApiErrorMessage } from '../api';

export default function ObjectWorkPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [works, setWorks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    worksApi.bySession(sessionId)
      .then((r) => setWorks(r.data))
      .catch((err) => setError(getApiErrorMessage(err, 'Ошибка загрузки работ по объекту')))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return <Box sx={{ textAlign: 'center', mt: 8 }}><CircularProgress /></Box>;

  const totalCost = works.reduce((sum, w) => sum + parseFloat(w.total || 0), 0);

  return (
    <Box sx={{ pb: 10 }}>
      <Typography variant="h5" gutterBottom>Работы на объекте</Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {works.length > 0 ? (
        <>
          {works.map((w) => (
            <Card key={w.id} elevation={1} sx={{ mb: 1.5 }}>
              <CardContent sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                <Avatar sx={{ bgcolor: 'primary.light', width: 40, height: 40 }}>
                  <BuildIcon sx={{ fontSize: 20 }} />
                </Avatar>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle2">{w.work_name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {w.volume} {w.unit || ''} &times; {parseFloat(w.rate || 0).toLocaleString('ru-RU')} = {parseFloat(w.total || 0).toLocaleString('ru-RU')} руб.
                  </Typography>
                </Box>
                {w.has_photos
                  ? <Chip icon={<PhotoCameraIcon />} label="Фото" size="small" color="success" />
                  : <Chip icon={<PhotoCameraIcon />} label="Нет" size="small" color="warning" />
                }
              </CardContent>
            </Card>
          ))}
          <Card elevation={2} sx={{ mb: 2, bgcolor: 'primary.main', color: 'white' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="body2">Итого</Typography>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {totalCost.toLocaleString('ru-RU')} руб.
              </Typography>
            </CardContent>
          </Card>
        </>
      ) : (
        <Card elevation={0} sx={{ py: 4, textAlign: 'center', bgcolor: 'grey.50' }}>
          <BuildIcon sx={{ fontSize: 48, color: 'grey.400', mb: 1 }} />
          <Typography color="text.secondary">Работы ещё не добавлены</Typography>
          <Typography variant="body2" color="text.secondary">Нажмите + чтобы добавить</Typography>
        </Card>
      )}

      <Button variant="outlined" color="error" startIcon={<ExitToAppIcon />} fullWidth onClick={() => navigate(`/depart/${sessionId}`)} sx={{ mt: 2 }}>
        Покинуть объект
      </Button>

      <Fab color="primary" sx={{ position: 'fixed', bottom: 90, right: 16, zIndex: 1200 }} onClick={() => navigate(`/add-work/${sessionId}`)}>
        <AddIcon />
      </Fab>
    </Box>
  );
}
