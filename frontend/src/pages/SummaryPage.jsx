import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, CircularProgress, Alert,
  Chip, Divider, List, ListItem, ListItemText,
} from '@mui/material';
import { workdayApi } from '../api';

const statusLabels = {
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
      .catch(() => setError('Ошибка загрузки'))
      .finally(() => setLoading(false));
  }, [workdayId]);

  if (loading) return <Box sx={{ textAlign: 'center', mt: 4 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!summary) return null;

  const st = statusLabels[summary.status] || { label: summary.status, color: 'default' };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Итог дня</Typography>

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="h6">{summary.date}</Typography>
            <Chip label={st.label} color={st.color} />
          </Box>
          <Typography variant="body2">Бригада: {summary.brigade}</Typography>
          <Typography variant="body2">Мастер: {summary.foreman}</Typography>
          {summary.total_hours && (
            <Typography variant="h5" sx={{ mt: 1 }}>
              {summary.total_hours} ч
            </Typography>
          )}
        </CardContent>
      </Card>

      {/* Объекты и работы */}
      {summary.sessions?.map((session, idx) => (
        <Card key={idx} sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              {session.object}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {session.arrived_at && new Date(session.arrived_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
              {session.departed_at && ` — ${new Date(session.departed_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`}
              {session.duration_minutes && ` (${session.duration_minutes} мин)`}
            </Typography>
            <Divider sx={{ my: 1 }} />
            {session.works?.length > 0 ? (
              <List disablePadding dense>
                {session.works.map((w) => (
                  <ListItem key={w.id} disablePadding>
                    <ListItemText
                      primary={w.name}
                      secondary={`${w.volume} ${w.unit || ''} x ${parseFloat(w.rate).toLocaleString('ru-RU')} = ${parseFloat(w.cost).toLocaleString('ru-RU')} руб.`}
                    />
                    {!w.has_photos && <Chip label="Нет фото" size="small" color="warning" />}
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Работы не зафиксированы
              </Typography>
            )}
          </CardContent>
        </Card>
      ))}

      {/* Итоги */}
      <Card sx={{ bgcolor: 'primary.main', color: 'white' }}>
        <CardContent>
          <Typography variant="body2">Всего работ: {summary.total_works}</Typography>
          <Typography variant="h5">
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
