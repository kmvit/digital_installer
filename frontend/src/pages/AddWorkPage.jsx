import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box, Button, Typography, Alert, TextField, Autocomplete,
  CircularProgress,
} from '@mui/material';
import PhotoCapture from '../components/PhotoCapture';
import { worksApi, mobileApi, getApiErrorMessage } from '../api';

export default function AddWorkPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [priceItems, setPriceItems] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [volume, setVolume] = useState('');
  const [comment, setComment] = useState('');
  const [photo, setPhoto] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingItems, setLoadingItems] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    // Загрузить все позиции прайса
    mobileApi.priceItems()
      .then((r) => setPriceItems(r.data?.results || r.data || []))
      .catch((err) => setError(getApiErrorMessage(err, 'Не удалось загрузить список работ')))
      .finally(() => setLoadingItems(false));
  }, []);

  const handleSubmit = async () => {
    if (!selectedItem || !volume) {
      setError('Выберите вид работы и укажите объём');
      return;
    }
    setLoading(true);
    setError('');

    try {
      const { data: work } = await worksApi.create(sessionId, {
        price_list_item: selectedItem.id,
        volume: parseFloat(volume),
        comment,
      });

      // Прикрепить фото, если есть
      if (photo) {
        const fd = new FormData();
        fd.append('photo', photo);
        await worksApi.addPhoto(work.id, fd);
      }

      navigate(`/object/${sessionId}`);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Ошибка при сохранении работы'));
    } finally {
      setLoading(false);
    }
  };

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
          <TextField {...params} label="Вид работы *" fullWidth />
        )}
        sx={{ mb: 2 }}
      />

      {selectedItem && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Единица: {selectedItem.unit || '—'} | Расценка: {selectedItem.base_rate || '—'} руб.
        </Typography>
      )}

      <TextField
        label="Объём *"
        type="number"
        value={volume}
        onChange={(e) => setVolume(e.target.value)}
        fullWidth
        sx={{ mb: 2 }}
        inputProps={{ step: '0.01', min: '0' }}
      />

      <PhotoCapture onPhoto={setPhoto} label="Фото выполненной работы" />

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
