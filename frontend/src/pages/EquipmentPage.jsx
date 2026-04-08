import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box, Button, Typography, Alert, TextField, Card, CardContent,
  ToggleButtonGroup, ToggleButton, CircularProgress, IconButton,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import { workdayApi } from '../api';

export default function EquipmentPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const type = searchParams.get('type') || 'morning';
  const [items, setItems] = useState([{ name: '', status: 'ok', notes: '' }]);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [workdayId, setWorkdayId] = useState(null);

  useEffect(() => {
    workdayApi.current()
      .then((r) => setWorkdayId(r.data.id))
      .catch(() => setError('Нет открытой смены'));
  }, []);

  const addItem = () => setItems([...items, { name: '', status: 'ok', notes: '' }]);

  const removeItem = (idx) => setItems(items.filter((_, i) => i !== idx));

  const updateItem = (idx, field, value) => {
    const updated = [...items];
    updated[idx] = { ...updated[idx], [field]: value };
    setItems(updated);
  };

  const handleSubmit = async () => {
    const validItems = items.filter((i) => i.name.trim());
    if (!validItems.length) {
      setError('Добавьте хотя бы одну позицию');
      return;
    }
    setLoading(true);
    setError('');

    try {
      await workdayApi.submitEquipment(workdayId, {
        checklist_type: type,
        notes,
        items: validItems,
      });
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка сохранения');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        {type === 'morning' ? 'Приём оборудования' : 'Возврат оборудования'}
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {items.map((item, idx) => (
        <Card key={idx} sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <TextField
                label="Название"
                value={item.name}
                onChange={(e) => updateItem(idx, 'name', e.target.value)}
                fullWidth
                size="small"
              />
              <IconButton color="error" onClick={() => removeItem(idx)} size="small">
                <DeleteIcon />
              </IconButton>
            </Box>
            <ToggleButtonGroup
              value={item.status}
              exclusive
              onChange={(_, val) => val && updateItem(idx, 'status', val)}
              size="small"
              sx={{ mt: 1 }}
            >
              <ToggleButton value="ok" color="success">В наличии</ToggleButton>
              <ToggleButton value="missing" color="error">Нет</ToggleButton>
              <ToggleButton value="damaged" color="warning">Повреждён</ToggleButton>
            </ToggleButtonGroup>
          </CardContent>
        </Card>
      ))}

      <Button
        variant="outlined"
        startIcon={<AddIcon />}
        onClick={addItem}
        fullWidth
        sx={{ mb: 2 }}
      >
        Добавить позицию
      </Button>

      <TextField
        label="Примечания"
        multiline
        rows={2}
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        fullWidth
        sx={{ mb: 2 }}
      />

      <Button
        variant="contained"
        size="large"
        fullWidth
        onClick={handleSubmit}
        disabled={loading || !workdayId}
      >
        {loading ? <CircularProgress size={24} /> : 'Сохранить чек-лист'}
      </Button>
    </Box>
  );
}
