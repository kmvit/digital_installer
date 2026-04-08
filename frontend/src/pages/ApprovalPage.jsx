import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Typography, Card, CardContent, Alert,
  CircularProgress, TextField, Dialog, DialogTitle,
  DialogContent, DialogActions, Chip,
} from '@mui/material';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import { workdayApi } from '../api';

export default function ApprovalPage() {
  const navigate = useNavigate();
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dialog, setDialog] = useState(null); // { id, action: 'approve'|'reject' }
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const load = () => {
    setLoading(true);
    workdayApi.pendingApproval()
      .then((r) => setPending(r.data))
      .catch(() => setError('Ошибка загрузки'))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleAction = async () => {
    if (!dialog) return;
    setSubmitting(true);

    try {
      if (dialog.action === 'approve') {
        await workdayApi.approve(dialog.id, { comment });
      } else {
        await workdayApi.reject(dialog.id, { comment });
      }
      setDialog(null);
      setComment('');
      load();
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <Box sx={{ textAlign: 'center', mt: 4 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Приёмка отчётов</Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {pending.length === 0 ? (
        <Typography color="text.secondary" align="center" sx={{ mt: 4 }}>
          Нет отчётов, ожидающих приёмки
        </Typography>
      ) : (
        pending.map((wd) => (
          <Card key={wd.id} sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                {wd.brigade_name} — {wd.date}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Мастер: {wd.foreman_name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Объектов: {wd.sessions_count}
              </Typography>

              <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => navigate(`/summary/${wd.id}`)}
                >
                  Детали
                </Button>
                <Button
                  variant="contained"
                  color="success"
                  size="small"
                  startIcon={<CheckIcon />}
                  onClick={() => setDialog({ id: wd.id, action: 'approve' })}
                >
                  Принять
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  size="small"
                  startIcon={<CloseIcon />}
                  onClick={() => setDialog({ id: wd.id, action: 'reject' })}
                >
                  Отклонить
                </Button>
              </Box>
            </CardContent>
          </Card>
        ))
      )}

      {/* Диалог подтверждения */}
      <Dialog open={!!dialog} onClose={() => setDialog(null)} fullWidth>
        <DialogTitle>
          {dialog?.action === 'approve' ? 'Принять отчёт?' : 'Отклонить отчёт?'}
        </DialogTitle>
        <DialogContent>
          <TextField
            label="Комментарий"
            multiline
            rows={3}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            fullWidth
            sx={{ mt: 1 }}
            placeholder={dialog?.action === 'reject' ? 'Укажите причину отклонения' : 'Необязательно'}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setDialog(null); setComment(''); }}>Отмена</Button>
          <Button
            onClick={handleAction}
            variant="contained"
            color={dialog?.action === 'approve' ? 'success' : 'error'}
            disabled={submitting}
          >
            {submitting ? <CircularProgress size={20} /> :
              dialog?.action === 'approve' ? 'Принять' : 'Отклонить'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
