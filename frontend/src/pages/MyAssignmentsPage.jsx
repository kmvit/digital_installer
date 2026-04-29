import { useState, useEffect } from 'react';
import {
  Box, Typography, Alert, Card, CardContent, Button, Chip, CircularProgress, Divider,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CheckIcon from '@mui/icons-material/Check';
import PhotoCapture from '../components/PhotoCapture';
import { worksApi, getApiErrorMessage } from '../api';

const STATUS_COLORS = { assigned: 'default', in_progress: 'warning', completed: 'success' };
const STATUS_LABELS = { assigned: 'Назначена', in_progress: 'В работе', completed: 'Выполнена' };

export default function MyAssignmentsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeWork, setActiveWork] = useState(null);
  const [mode, setMode] = useState(null); // 'start' | 'finish'
  const [photo, setPhoto] = useState(null);
  const [photoMeta, setPhotoMeta] = useState(null);
  const [factVolume, setFactVolume] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const load = () => {
    setLoading(true);
    worksApi.myAssignments()
      .then((r) => setItems(r.data || []))
      .catch((err) => setError(getApiErrorMessage(err, 'Не удалось загрузить мои работы')))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const openMode = (work, m) => {
    setActiveWork(work);
    setMode(m);
    setPhoto(null);
    setPhotoMeta(null);
    setFactVolume(work.planned_volume || '');
  };

  const closeMode = () => {
    setActiveWork(null); setMode(null); setPhoto(null); setPhotoMeta(null); setFactVolume('');
  };

  const submit = async () => {
    if (!photo) { setError('Сделайте фото'); return; }
    setSubmitting(true);
    setError('');
    const fd = new FormData();
    fd.append('photo', photo);
    if (photoMeta?.captured_at) fd.append('captured_at', photoMeta.captured_at);
    if (photoMeta?.latitude != null) fd.append('latitude', photoMeta.latitude);
    if (photoMeta?.longitude != null) fd.append('longitude', photoMeta.longitude);
    if (mode === 'finish') fd.append('volume', factVolume);
    try {
      if (mode === 'start') await worksApi.start(activeWork.id, fd);
      else await worksApi.finish(activeWork.id, fd);
      closeMode();
      load();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Ошибка'));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <Box sx={{ textAlign: 'center', mt: 8 }}><CircularProgress /></Box>;

  if (activeWork) {
    return (
      <Box>
        <Typography variant="h6" gutterBottom>
          {mode === 'start' ? 'Начать работу' : 'Завершить работу'}
        </Typography>
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle2">{activeWork.work_name}</Typography>
            <Typography variant="body2" color="text.secondary">
              Объект: {activeWork.object_name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              План: {activeWork.planned_volume} {activeWork.unit || ''}
            </Typography>
          </CardContent>
        </Card>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        {mode === 'finish' && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>Фактический объём</Typography>
            <input
              type="number" step="0.01" min="0"
              value={factVolume}
              onChange={(e) => setFactVolume(e.target.value)}
              style={{ width: '100%', padding: 10, fontSize: 16, borderRadius: 4, border: '1px solid #999' }}
            />
          </Box>
        )}
        <PhotoCapture
          onPhoto={(f, m) => { setPhoto(f); setPhotoMeta(m || null); }}
          label={mode === 'start' ? 'Фото начала работы' : 'Фото завершения'}
          required
          inputId={`assign-${mode}`}
        />
        <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
          <Button variant="outlined" onClick={closeMode} sx={{ flex: 1 }}>Отмена</Button>
          <Button variant="contained" onClick={submit} disabled={submitting || !photo} sx={{ flex: 2 }}>
            {submitting ? <CircularProgress size={24} /> : (mode === 'start' ? 'Начал' : 'Завершил')}
          </Button>
        </Box>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Мои работы</Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {items.length === 0 ? (
        <Card elevation={0} sx={{ py: 4, textAlign: 'center', bgcolor: 'grey.50' }}>
          <Typography color="text.secondary">Пока нет назначенных работ</Typography>
        </Card>
      ) : items.map((w) => (
        <Card key={w.id} elevation={1} sx={{ mb: 1.5 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="subtitle2">{w.work_name}</Typography>
              <Chip label={STATUS_LABELS[w.status]} size="small" color={STATUS_COLORS[w.status]} />
            </Box>
            <Typography variant="body2" color="text.secondary">{w.object_name}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              План: {w.planned_volume} {w.unit || ''}
              {w.status === 'completed' && ` · Факт: ${w.volume}`}
            </Typography>
            <Divider sx={{ mb: 1 }} />
            <Box sx={{ display: 'flex', gap: 1 }}>
              {w.status === 'assigned' && (
                <Button size="small" startIcon={<PlayArrowIcon />} variant="contained" onClick={() => openMode(w, 'start')}>
                  Начал
                </Button>
              )}
              {w.status === 'in_progress' && (
                <Button size="small" startIcon={<CheckIcon />} variant="contained" color="success" onClick={() => openMode(w, 'finish')}>
                  Завершил
                </Button>
              )}
            </Box>
          </CardContent>
        </Card>
      ))}
    </Box>
  );
}
