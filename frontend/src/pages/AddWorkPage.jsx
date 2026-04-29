import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box, Button, Typography, Alert, TextField, Autocomplete,
  CircularProgress,
} from '@mui/material';
import PhotoCapture from '../components/PhotoCapture';
import { worksApi, mobileApi, authApi, getApiErrorMessage } from '../api';
import { Switch, FormControlLabel } from '@mui/material';

export default function AddWorkPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [priceItems, setPriceItems] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [volume, setVolume] = useState('');
  const [comment, setComment] = useState('');
  const [members, setMembers] = useState([]);
  const [assignedTo, setAssignedTo] = useState(null);
  const [assignMode, setAssignMode] = useState(false);
  const [photo, setPhoto] = useState(null);
  const [photoMeta, setPhotoMeta] = useState(null);
  const handlePhoto = (file, meta) => { setPhoto(file); setPhotoMeta(meta || null); };
  const [loading, setLoading] = useState(false);
  const [loadingItems, setLoadingItems] = useState(true);
  const [error, setError] = useState('');
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
    // Загрузить позиции прайса, разрешённые для объекта этой сессии
    mobileApi.priceItems({ session_id: sessionId })
      .then((r) => setPriceItems(r.data?.results || r.data || []))
      .catch((err) => setError(getApiErrorMessage(err, 'Не удалось загрузить список работ')))
      .finally(() => setLoadingItems(false));
    mobileApi.myBrigade()
      .then((r) => setMembers(r.data.members || []))
      .catch(() => {});
  }, [sessionId]);

  const handleSubmit = async () => {
    if (!selectedItem || !volume) {
      setError('Выберите вид работы и укажите объём');
      return;
    }
    if (assignMode && !assignedTo) {
      setError('Выберите монтажника, которому назначаете работу');
      return;
    }
    setLoading(true);
    setError('');

    try {
      const payload = {
        price_list_item: selectedItem.id,
        comment,
      };
      if (assignMode) {
        payload.planned_volume = parseFloat(volume);
        payload.volume = 0;
        payload.assigned_to = assignedTo.id;
      } else {
        payload.volume = parseFloat(volume);
      }
      const { data: work } = await worksApi.create(sessionId, payload);

      // Прикрепить фото, если есть
      if (photo) {
        const fd = new FormData();
        fd.append('photo', photo);
        if (photoMeta?.captured_at) fd.append('captured_at', photoMeta.captured_at);
        if (photoMeta?.latitude != null) fd.append('latitude', photoMeta.latitude);
        if (photoMeta?.longitude != null) fd.append('longitude', photoMeta.longitude);
        await worksApi.addPhoto(work.id, fd);
      }

      navigate(`/object/${sessionId}`);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Ошибка при сохранении работы'));
    } finally {
      setLoading(false);
    }
  };

  if (forbidden) {
    return (
      <Box>
        <Typography variant="h5" gutterBottom>Добавить работу</Typography>
        <Alert severity="warning">
          Добавлять работы может только бригадир. Если нужно зафиксировать выполнение —
          обратитесь к мастеру: он назначит работу, а вы сможете нажать «Начал»/«Завершил» в «Моих работах».
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Добавить работу</Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Autocomplete
        options={priceItems}
        getOptionLabel={(o) => `${o.item_number || ''} ${o.name}`}
        value={selectedItem}
        onChange={(_, val) => setSelectedItem(val)}
        loading={loadingItems}
        renderInput={(params) => (
          <TextField {...params} label="Работа *" fullWidth />
        )}
        sx={{ mb: 2 }}
      />

      {selectedItem && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Единица: {selectedItem.unit || '—'} | Расценка: {selectedItem.base_rate || '—'} руб.
        </Typography>
      )}

      <TextField
        label={assignMode ? 'Плановый объём *' : 'Объём *'}
        type="number"
        value={volume}
        onChange={(e) => setVolume(e.target.value)}
        fullWidth
        sx={{ mb: 2 }}
        inputProps={{ step: '0.01', min: '0' }}
      />

      <FormControlLabel
        control={<Switch checked={assignMode} onChange={(e) => setAssignMode(e.target.checked)} />}
        label="Назначить монтажнику"
        sx={{ mb: 1 }}
      />
      {assignMode && (
        <Autocomplete
          options={members}
          getOptionLabel={(o) => o.last_name && o.first_name ? `${o.last_name} ${o.first_name}` : o.username}
          value={assignedTo}
          onChange={(_, val) => setAssignedTo(val)}
          renderInput={(params) => (<TextField {...params} label="Монтажник *" fullWidth />)}
          sx={{ mb: 2 }}
        />
      )}

      {!assignMode && (
        <PhotoCapture onPhoto={handlePhoto} label="Фото выполненной работы" />
      )}

      <TextField
        label="Комментарий"
        multiline
        rows={2}
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        fullWidth
        sx={{ mb: 2 }}
      />

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button variant="outlined" onClick={() => navigate(-1)} sx={{ flex: 1 }}>
          Отмена
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={loading || !selectedItem || !volume}
          sx={{ flex: 2 }}
        >
          {loading ? <CircularProgress size={24} /> : 'Сохранить'}
        </Button>
      </Box>
    </Box>
  );
}
