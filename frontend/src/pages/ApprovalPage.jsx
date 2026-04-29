import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Typography, Card, CardContent, Alert,
  CircularProgress, TextField, Dialog, DialogTitle,
  DialogContent, DialogActions, Chip, Grid, Stack,
} from '@mui/material';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import VisibilityIcon from '@mui/icons-material/Visibility';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { workdayApi, getApiErrorMessage } from '../api';

function PhotoTile({ src, label, onOpen }) {
  if (!src) return null;
  return (
    <Box
      onClick={() => onOpen?.({ src, label })}
      sx={{
        position: 'relative',
        width: 110,
        borderRadius: 1.5,
        overflow: 'hidden',
        border: '1px solid #ddd',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        cursor: 'pointer',
        '&:hover': { boxShadow: '0 2px 6px rgba(0,0,0,0.18)' },
      }}
    >
      <Box
        component="img"
        src={src}
        alt={label}
        sx={{ width: '100%', height: 110, objectFit: 'cover', display: 'block' }}
      />
      <Typography
        variant="caption"
        sx={{
          position: 'absolute',
          left: 0, right: 0, bottom: 0,
          px: 0.75, py: 0.25,
          background: 'linear-gradient(to top, rgba(0,0,0,0.65), rgba(0,0,0,0))',
          color: '#fff',
          fontWeight: 600,
          fontSize: 11,
          letterSpacing: 0.2,
          textAlign: 'center',
          textTransform: 'uppercase',
        }}
      >
        {label}
      </Typography>
    </Box>
  );
}

function PreviewDialog({ open, onClose, summary }) {
  const [lightbox, setLightbox] = useState(null);
  if (!summary) return null;
  const q = summary.quality || {};
  const openLightbox = (item) => setLightbox(item);
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>Отчёт {summary.brigade} — {summary.date}</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2}>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip
              icon={q.all_works_have_photos ? <CheckIcon /> : <WarningAmberIcon />}
              label={`Фото работ: ${q.all_works_have_photos ? 'все' : `нет у ${q.works_without_photos}`}`}
              color={q.all_works_have_photos ? 'success' : 'warning'}
              size="small"
            />
            <Chip
              icon={q.all_sessions_have_scheme ? <CheckIcon /> : <WarningAmberIcon />}
              label={`Схема работ: ${q.all_sessions_have_scheme ? 'все' : `нет у ${q.sessions_without_scheme}`}`}
              color={q.all_sessions_have_scheme ? 'success' : 'warning'}
              size="small"
            />
            <Chip
              icon={q.all_workers_gps_checked ? <CheckIcon /> : <WarningAmberIcon />}
              label={`GPS-чек: ${q.all_workers_gps_checked ? 'все' : `${q.gps_checks_missing} не подтвердили`}`}
              color={q.all_workers_gps_checked ? 'success' : 'warning'}
              size="small"
            />
          </Box>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>Открытие/закрытие смены</Typography>
              <Grid container spacing={1}>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">
                    Clock-in: {summary.clock_in_at ? new Date(summary.clock_in_at).toLocaleString('ru-RU') : '—'}
                  </Typography>
                  {summary.clock_in_lat && (
                    <Typography variant="caption" display="block" color="text.secondary">
                      GPS: {summary.clock_in_lat}, {summary.clock_in_lng}
                    </Typography>
                  )}
                  <PhotoTile src={summary.clock_in_photo} label="Фото начала" onOpen={openLightbox} />
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">
                    Clock-out: {summary.clock_out_at ? new Date(summary.clock_out_at).toLocaleString('ru-RU') : '—'}
                  </Typography>
                  {summary.clock_out_lat && (
                    <Typography variant="caption" display="block" color="text.secondary">
                      GPS: {summary.clock_out_lat}, {summary.clock_out_lng}
                    </Typography>
                  )}
                  <PhotoTile src={summary.clock_out_photo} label="Фото завершения" onOpen={openLightbox} />
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {summary.gps_checks?.length > 0 && (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>GPS-проверка бригады</Typography>
                <Stack spacing={0.5}>
                  {summary.gps_checks.map((g) => (
                    <Box key={g.user_id} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2">{g.name}</Typography>
                      {g.checked
                        ? <Chip size="small" color="success" label={new Date(g.captured_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })} />
                        : <Chip size="small" color="warning" label="Не подтвердил" />}
                    </Box>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          )}

          {summary.sessions?.map((s, idx) => (
            <Card key={s.session_id || idx} variant="outlined">
              <CardContent>
                <Typography variant="subtitle2">{s.object}</Typography>
                <Typography variant="caption" color="text.secondary" display="block">
                  {new Date(s.arrived_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                  {s.departed_at && ` — ${new Date(s.departed_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`}
                  {s.duration_minutes && ` (${s.duration_minutes} мин)`}
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap' }}>
                  <PhotoTile src={s.arrived_photo} label="Прибытие" onOpen={openLightbox} />
                  <PhotoTile src={s.departed_photo} label="Убытие" onOpen={openLightbox} />
                  <PhotoTile src={s.scheme_photo} label="Схема" onOpen={openLightbox} />
                </Stack>
                {s.works?.length > 0 && (
                  <Stack spacing={1} sx={{ mt: 2 }}>
                    {s.works.map((w) => (
                      <Box key={w.id} sx={{ p: 1, border: '1px solid #eee', borderRadius: 1 }}>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>{w.name}</Typography>
                        <Typography variant="caption" color="text.secondary" display="block">
                          {w.volume} {w.unit || ''} · {parseFloat(w.cost).toLocaleString('ru-RU')} ₽
                          {w.assigned_to_name && ` · ${w.assigned_to_name}`}
                        </Typography>
                        <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
                          <PhotoTile src={w.started_photo} label="Начал" onOpen={openLightbox} />
                          <PhotoTile src={w.completed_photo} label="Завершил" onOpen={openLightbox} />
                          {(w.extra_photos || []).map((p, i) => (
                            <PhotoTile key={i} src={p} label="Доп." onOpen={openLightbox} />
                          ))}
                        </Stack>
                        {!w.has_photos && (
                          <Chip size="small" color="warning" icon={<WarningAmberIcon />} label="Без фото" sx={{ mt: 0.5 }} />
                        )}
                        {w.comment && (
                          <Typography variant="caption" color="text.secondary" display="block">
                            Комментарий: {w.comment}
                          </Typography>
                        )}
                      </Box>
                    ))}
                  </Stack>
                )}
              </CardContent>
            </Card>
          ))}

          {summary.equipment_diff?.length > 0 && (
            <Card variant="outlined" sx={{ borderColor: 'warning.main' }}>
              <CardContent>
                <Typography variant="subtitle2" color="warning.main">Расхождения по инструменту</Typography>
                {summary.equipment_diff.map((d, i) => (
                  <Typography variant="body2" key={i}>
                    {d.name}: утром «{d.morning || '—'}», вечером «{d.evening || '—'}»
                  </Typography>
                ))}
              </CardContent>
            </Card>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Закрыть</Button>
      </DialogActions>

      <Dialog open={!!lightbox} onClose={() => setLightbox(null)} maxWidth="lg">
        <Box sx={{ position: 'relative', bgcolor: 'black' }}>
          <Button
            onClick={() => setLightbox(null)}
            sx={{ position: 'absolute', top: 8, right: 8, zIndex: 10, bgcolor: 'rgba(255,255,255,0.85)', minWidth: 0, px: 1.5 }}
          >
            ✕
          </Button>
          {lightbox && (
            <Box
              component="img"
              src={lightbox.src}
              alt={lightbox.label}
              sx={{ display: 'block', maxWidth: '90vw', maxHeight: '85vh', objectFit: 'contain' }}
            />
          )}
          {lightbox?.label && (
            <Typography
              sx={{
                position: 'absolute', left: 0, right: 0, bottom: 0,
                px: 2, py: 1, color: '#fff',
                background: 'linear-gradient(to top, rgba(0,0,0,0.7), rgba(0,0,0,0))',
                textAlign: 'center', textTransform: 'uppercase', fontWeight: 600,
              }}
            >
              {lightbox.label}
            </Typography>
          )}
        </Box>
      </Dialog>
    </Dialog>
  );
}

export default function ApprovalPage() {
  const navigate = useNavigate();
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dialog, setDialog] = useState(null);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [previewSummary, setPreviewSummary] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const load = () => {
    setLoading(true);
    workdayApi.pendingApproval()
      .then((r) => setPending(r.data))
      .catch((err) => setError(getApiErrorMessage(err, 'Ошибка загрузки отчётов')))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const openPreview = async (id) => {
    setPreviewLoading(true);
    try {
      const { data } = await workdayApi.summary(id);
      setPreviewSummary(data);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Не удалось загрузить отчёт'));
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleAction = async () => {
    if (!dialog) return;
    setSubmitting(true);
    try {
      if (dialog.action === 'approve') await workdayApi.approve(dialog.id, { comment });
      else await workdayApi.reject(dialog.id, { comment });
      setDialog(null);
      setComment('');
      load();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Ошибка при обработке отчёта'));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <Box sx={{ textAlign: 'center', mt: 4 }}><CircularProgress /></Box>;

  const overdueCount = pending.filter((p) => p.is_overdue).length;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Приёмка отчётов</Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {overdueCount > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {overdueCount} отчёт(ов) ожидает приёмки более суток. Неутверждённые отчёты не идут в расчёт ЗП.
        </Alert>
      )}

      {pending.length === 0 ? (
        <Typography color="text.secondary" align="center" sx={{ mt: 4 }}>
          Нет отчётов, ожидающих приёмки
        </Typography>
      ) : pending.map((wd) => (
        <Card key={wd.id} sx={{ mb: 2, borderLeft: 4, borderColor: wd.is_overdue ? 'warning.main' : 'transparent' }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
              <Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                  {wd.brigade_name} — {wd.date}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Мастер: {wd.foreman_name} · Объектов: {wd.sessions_count}
                </Typography>
              </Box>
              {wd.is_overdue && (
                <Chip size="small" color="warning" icon={<WarningAmberIcon />} label={`Просрочено ${wd.overdue_days} дн.`} />
              )}
            </Box>

            <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
              <Button size="small" variant="outlined" startIcon={<VisibilityIcon />} onClick={() => openPreview(wd.id)}>
                Просмотр
              </Button>
              <Button size="small" variant="text" onClick={() => navigate(`/summary/${wd.id}`)}>
                Полный отчёт
              </Button>
              <Button
                variant="contained" color="success" size="small"
                startIcon={<CheckIcon />}
                onClick={() => setDialog({ id: wd.id, action: 'approve' })}
              >
                Принять
              </Button>
              <Button
                variant="outlined" color="error" size="small"
                startIcon={<CloseIcon />}
                onClick={() => setDialog({ id: wd.id, action: 'reject' })}
              >
                Отклонить
              </Button>
            </Box>
          </CardContent>
        </Card>
      ))}

      <Dialog open={!!dialog} onClose={() => setDialog(null)} fullWidth>
        <DialogTitle>{dialog?.action === 'approve' ? 'Принять отчёт?' : 'Отклонить отчёт?'}</DialogTitle>
        <DialogContent>
          <TextField
            label="Комментарий" multiline rows={3} value={comment}
            onChange={(e) => setComment(e.target.value)} fullWidth sx={{ mt: 1 }}
            placeholder={dialog?.action === 'reject' ? 'Укажите причину отклонения' : 'Необязательно'}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setDialog(null); setComment(''); }}>Отмена</Button>
          <Button
            onClick={handleAction} variant="contained"
            color={dialog?.action === 'approve' ? 'success' : 'error'}
            disabled={submitting}
          >
            {submitting ? <CircularProgress size={20} /> : (dialog?.action === 'approve' ? 'Принять' : 'Отклонить')}
          </Button>
        </DialogActions>
      </Dialog>

      <PreviewDialog
        open={!!previewSummary || previewLoading}
        onClose={() => { setPreviewSummary(null); }}
        summary={previewSummary}
      />
    </Box>
  );
}
