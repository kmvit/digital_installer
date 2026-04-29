import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box, Button, Typography, Alert, Card, CardContent,
  CircularProgress, Chip, Avatar, IconButton,
  Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Autocomplete, MenuItem, Stack,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import ExitToAppIcon from '@mui/icons-material/ExitToApp';
import BuildIcon from '@mui/icons-material/Build';
import PhotoCameraIcon from '@mui/icons-material/PhotoCamera';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { worksApi, mobileApi, authApi, getApiErrorMessage } from '../api';

const STATUS_OPTIONS = [
  { value: 'assigned', label: 'Назначена' },
  { value: 'in_progress', label: 'В работе' },
  { value: 'completed', label: 'Выполнена' },
];
const STATUS_LABELS = Object.fromEntries(STATUS_OPTIONS.map((o) => [o.value, o.label]));
const STATUS_COLORS = { assigned: 'default', in_progress: 'warning', completed: 'success' };

export default function ObjectWorkPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [works, setWorks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [role, setRole] = useState(null);
  const [members, setMembers] = useState([]);
  const [editing, setEditing] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [editError, setEditError] = useState('');
  const [editSaving, setEditSaving] = useState(false);

  const reload = () => {
    worksApi.bySession(sessionId)
      .then((r) => setWorks(r.data))
      .catch((err) => setError(getApiErrorMessage(err, 'Ошибка загрузки работ по объекту')))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    reload();
    authApi.me().then((r) => setRole(r.data?.role)).catch(() => {});
    mobileApi.myBrigade().then((r) => setMembers(r.data?.members || [])).catch(() => {});
  }, [sessionId]);

  const canManage = role && ['foreman', 'administrator', 'director'].includes(role);

  const openEdit = (w) => {
    setEditError('');
    setEditing(w);
    setEditForm({
      planned_volume: w.planned_volume ?? '',
      volume: w.volume ?? '',
      assigned_to: members.find((m) => m.id === w.assigned_to) || null,
      status: w.status,
      comment: w.comment || '',
    });
  };

  const closeEdit = () => { setEditing(null); setEditForm({}); setEditError(''); };

  const saveEdit = async () => {
    setEditSaving(true);
    setEditError('');
    try {
      const payload = {
        status: editForm.status,
        comment: editForm.comment,
      };
      if (editForm.planned_volume !== '') payload.planned_volume = parseFloat(editForm.planned_volume);
      if (editForm.volume !== '') payload.volume = parseFloat(editForm.volume);
      payload.assigned_to = editForm.assigned_to ? editForm.assigned_to.id : null;
      await worksApi.update(editing.id, payload);
      closeEdit();
      reload();
    } catch (err) {
      setEditError(getApiErrorMessage(err, 'Ошибка сохранения'));
    } finally {
      setEditSaving(false);
    }
  };

  const removeWork = async (w) => {
    if (!window.confirm(`Удалить работу «${w.work_name}»?`)) return;
    try {
      await worksApi.delete(w.id);
      reload();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Ошибка удаления'));
    }
  };

  if (loading) return <Box sx={{ textAlign: 'center', mt: 8 }}><CircularProgress /></Box>;

  const totalCost = works.reduce((sum, w) => sum + parseFloat(w.total || 0), 0);

  return (
    <Box sx={{ pb: 10 }}>
      <Typography variant="h5" gutterBottom>Работы на объекте</Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {works.length > 0 ? (
        <>
          {works.map((w) => {
            const isAssigned = w.status !== 'completed';
            return (
              <Card key={w.id} elevation={1} sx={{ mb: 1.5 }}>
                <CardContent sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                  <Avatar sx={{ bgcolor: 'primary.light', width: 40, height: 40 }}>
                    <BuildIcon sx={{ fontSize: 20 }} />
                  </Avatar>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="subtitle2">{w.work_name}</Typography>
                    {isAssigned ? (
                      <Typography variant="body2" color="text.secondary">
                        План: {w.planned_volume || w.volume} {w.unit || ''}
                        {w.assigned_to_name && ` · ${w.assigned_to_name}`}
                      </Typography>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        {w.volume} {w.unit || ''} &times; {parseFloat(w.rate || 0).toLocaleString('ru-RU')} = {parseFloat(w.total || 0).toLocaleString('ru-RU')} руб.
                      </Typography>
                    )}
                  </Box>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, alignItems: 'flex-end' }}>
                    <Chip label={STATUS_LABELS[w.status] || w.status} size="small" color={STATUS_COLORS[w.status] || 'default'} />
                    {w.has_photos
                      ? <Chip icon={<PhotoCameraIcon />} label="Фото" size="small" color="success" variant="outlined" />
                      : <Chip icon={<PhotoCameraIcon />} label="Нет" size="small" color="warning" variant="outlined" />
                    }
                    {canManage && (
                      <Box sx={{ display: 'flex', gap: 0 }}>
                        <IconButton size="small" onClick={() => openEdit(w)}><EditIcon fontSize="small" /></IconButton>
                        <IconButton size="small" color="error" onClick={() => removeWork(w)}><DeleteIcon fontSize="small" /></IconButton>
                      </Box>
                    )}
                  </Box>
                </CardContent>
              </Card>
            );
          })}
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
        </Card>
      )}

      {canManage && (
        <Button
          variant="contained"
          size="large"
          startIcon={<AddIcon />}
          fullWidth
          onClick={() => navigate(`/add-work/${sessionId}`)}
          sx={{ mt: 2, py: 1.5 }}
        >
          Добавить работу
        </Button>
      )}

      <Button
        variant="outlined"
        color="error"
        startIcon={<ExitToAppIcon />}
        fullWidth
        onClick={() => navigate(`/depart/${sessionId}`)}
        sx={{ mt: 1.5 }}
      >
        Покинуть объект
      </Button>

      <Dialog open={!!editing} onClose={closeEdit} fullWidth maxWidth="sm">
        <DialogTitle>Редактирование работы</DialogTitle>
        <DialogContent>
          {editing && (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Typography variant="body2" color="text.secondary">{editing.work_name}</Typography>
              {editError && <Alert severity="error">{editError}</Alert>}
              <TextField
                select label="Статус" value={editForm.status || ''}
                onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                fullWidth
              >
                {STATUS_OPTIONS.map((o) => <MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>)}
              </TextField>
              <Autocomplete
                options={members}
                getOptionLabel={(o) => o.last_name && o.first_name ? `${o.last_name} ${o.first_name}` : o.username}
                value={editForm.assigned_to || null}
                onChange={(_, val) => setEditForm({ ...editForm, assigned_to: val })}
                renderInput={(params) => <TextField {...params} label="Монтажник" fullWidth />}
                isOptionEqualToValue={(o, v) => o.id === v.id}
              />
              <TextField
                label="Плановый объём" type="number" value={editForm.planned_volume ?? ''}
                onChange={(e) => setEditForm({ ...editForm, planned_volume: e.target.value })}
                fullWidth inputProps={{ step: '0.01', min: '0' }}
              />
              <TextField
                label="Фактический объём" type="number" value={editForm.volume ?? ''}
                onChange={(e) => setEditForm({ ...editForm, volume: e.target.value })}
                fullWidth inputProps={{ step: '0.01', min: '0' }}
              />
              <TextField
                label="Комментарий" multiline rows={2} value={editForm.comment || ''}
                onChange={(e) => setEditForm({ ...editForm, comment: e.target.value })}
                fullWidth
              />
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeEdit}>Отмена</Button>
          <Button onClick={saveEdit} variant="contained" disabled={editSaving}>
            {editSaving ? <CircularProgress size={20} /> : 'Сохранить'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
