import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, CircularProgress, Alert,
  Chip, Divider, List, ListItem, ListItemText, ListItemIcon, Stack,
} from '@mui/material';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import BuildIcon from '@mui/icons-material/Build';
import { workdayApi, getApiErrorMessage } from '../api';

const statusConfig = {
  open: { label: 'Открыт', color: 'info' },
  closed: { label: 'Ожидает приёмки', color: 'warning' },
  approved: { label: 'Принят', color: 'success' },
  rejected: { label: 'Отклонён', color: 'error' },
};

export default function SummaryPage() {
  const { workdayId } = useParams();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    workdayApi.summary(workdayId)
      .then((r) => setSummary(r.data))
      .catch((err) => setError(getApiErrorMessage(err, 'Ошибка загрузки итогов смены')))
      .finally(() => setLoading(false));
  }, [workdayId]);

  if (loading) return <Box sx={{ textAlign: 'center', mt: 8 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!summary) return null;

  const st = statusConfig[summary.status] || { label: summary.status, color: 'default' };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Итог дня</Typography>

      <Card elevation={1} sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="h6">{summary.date}</Typography>
            <Chip label={st.label} color={st.color} />
          </Box>
          <Typography variant="body2" color="text.secondary">Бригада: {summary.brigade}</Typography>
          <Typography variant="body2" color="text.secondary">Мастер: {summary.foreman}</Typography>
          {summary.total_hours && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 2 }}>
              <AccessTimeIcon color="primary" />
              <Typography variant="h4" color="primary" sx={{ fontWeight: 700 }}>
                {summary.total_hours} ч
              </Typography>
            </Box>
          )}
          {summary.pm_comment && (
            <Alert severity={summary.status === 'rejected' ? 'error' : 'info'} sx={{ mt: 1 }}>
              Комментарий РП: {summary.pm_comment}
            </Alert>
          )}
        </CardContent>
      </Card>

      {summary.quality && (
        <Card elevation={1} sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>Качество отчёта</Typography>
            <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
              <Chip
                size="small"
                icon={summary.quality.all_works_have_photos ? <CheckCircleIcon /> : <WarningAmberIcon />}
                color={summary.quality.all_works_have_photos ? 'success' : 'warning'}
                label={summary.quality.all_works_have_photos ? 'Все работы с фото' : `Без фото: ${summary.quality.works_without_photos}`}
              />
              <Chip
                size="small"
                icon={summary.quality.all_sessions_have_scheme ? <CheckCircleIcon /> : <WarningAmberIcon />}
                color={summary.quality.all_sessions_have_scheme ? 'success' : 'warning'}
                label={summary.quality.all_sessions_have_scheme ? 'Все схемы' : `Без схемы: ${summary.quality.sessions_without_scheme}`}
              />
              <Chip
                size="small"
                icon={summary.quality.all_workers_gps_checked ? <CheckCircleIcon /> : <WarningAmberIcon />}
                color={summary.quality.all_workers_gps_checked ? 'success' : 'warning'}
                label={summary.quality.all_workers_gps_checked ? 'GPS-чек: все' : `GPS не подтвердили: ${summary.quality.gps_checks_missing}`}
              />
            </Stack>
          </CardContent>
        </Card>
      )}

      {(summary.clock_in_photo || summary.clock_out_photo) && (
        <Card elevation={1} sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>Открытие / закрытие смены</Typography>
            <Stack direction="row" spacing={2}>
              {summary.clock_in_photo && (
                <Box sx={{ textAlign: 'center' }}>
                  <a href={summary.clock_in_photo} target="_blank" rel="noreferrer">
                    <Box component="img" src={summary.clock_in_photo} alt="Clock-in" sx={{ width: 110, height: 110, objectFit: 'cover', borderRadius: 1, border: '1px solid #ddd' }} />
                  </a>
                  <Typography variant="caption" display="block">
                    {summary.clock_in_at && new Date(summary.clock_in_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                  </Typography>
                </Box>
              )}
              {summary.clock_out_photo && (
                <Box sx={{ textAlign: 'center' }}>
                  <a href={summary.clock_out_photo} target="_blank" rel="noreferrer">
                    <Box component="img" src={summary.clock_out_photo} alt="Clock-out" sx={{ width: 110, height: 110, objectFit: 'cover', borderRadius: 1, border: '1px solid #ddd' }} />
                  </a>
                  <Typography variant="caption" display="block">
                    {summary.clock_out_at && new Date(summary.clock_out_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                  </Typography>
                </Box>
              )}
            </Stack>
          </CardContent>
        </Card>
      )}

      {summary.sessions?.map((session, idx) => (
        <Card key={idx} elevation={1} sx={{ mb: 2, borderLeft: 4, borderColor: 'primary.main' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <LocationOnIcon color="primary" fontSize="small" />
              <Typography variant="subtitle1">{session.object}</Typography>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {session.arrived_at && new Date(session.arrived_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
              {session.departed_at && ` — ${new Date(session.departed_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`}
              {session.duration_minutes && ` (${session.duration_minutes} мин)`}
            </Typography>
            {(session.arrived_photo || session.departed_photo || session.scheme_photo) && (
              <Stack direction="row" spacing={1} sx={{ mb: 1, flexWrap: 'wrap' }}>
                {[
                  ['arrived_photo', 'Прибытие'],
                  ['departed_photo', 'Убытие'],
                  ['scheme_photo', 'Схема'],
                ].filter(([k]) => session[k]).map(([k, label]) => (
                  <Box key={k} sx={{ textAlign: 'center' }}>
                    <a href={session[k]} target="_blank" rel="noreferrer">
                      <Box component="img" src={session[k]} alt={label} sx={{ width: 80, height: 80, objectFit: 'cover', borderRadius: 1, border: '1px solid #ddd' }} />
                    </a>
                    <Typography variant="caption" display="block">{label}</Typography>
                  </Box>
                ))}
              </Stack>
            )}
            <Divider sx={{ my: 1 }} />
            {session.works?.length > 0 ? (
              <List disablePadding dense>
                {session.works.map((w) => (
                  <ListItem key={w.id} disablePadding sx={{ py: 0.5 }}>
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      <BuildIcon fontSize="small" color="action" />
                    </ListItemIcon>
                    <ListItemText
                      primary={w.name}
                      secondary={`${w.volume} ${w.unit || ''} = ${parseFloat(w.cost).toLocaleString('ru-RU')} руб.`}
                    />
                    {!w.has_photos && <Chip label="!" size="small" color="warning" />}
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary">Работы не зафиксированы</Typography>
            )}
          </CardContent>
        </Card>
      ))}

      <Card elevation={2} sx={{ bgcolor: 'primary.main', color: 'white' }}>
        <CardContent sx={{ textAlign: 'center', py: 3 }}>
          <Typography variant="body2" sx={{ opacity: 0.8 }}>Работ: {summary.total_works}</Typography>
          <Typography variant="h4" sx={{ fontWeight: 700, my: 0.5 }}>
            {parseFloat(summary.total_cost).toLocaleString('ru-RU')} руб.
          </Typography>
          {summary.works_without_photos > 0 && (
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              Без фото: {summary.works_without_photos}
            </Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
