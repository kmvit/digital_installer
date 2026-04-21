import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, CardActionArea, Chip,
  CircularProgress, Alert,
} from '@mui/material';
import { workdayApi, getApiErrorMessage } from '../api';

const statusLabels = {
  open: { label: 'Открыт', color: 'info' },
  closed: { label: 'Закрыт', color: 'warning' },
  approved: { label: 'Принят', color: 'success' },
  rejected: { label: 'Отклонён', color: 'error' },
};

export default function HistoryPage() {
  const navigate = useNavigate();
  const [days, setDays] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    workdayApi.history()
      .then((r) => setDays(r.data))
      .catch((err) => setError(getApiErrorMessage(err, 'Ошибка загрузки истории')))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Box sx={{ textAlign: 'center', mt: 4 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>История смен</Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {days.length === 0 ? (
        <Typography color="text.secondary" align="center" sx={{ mt: 4 }}>
          Пока нет данных
        </Typography>
      ) : (
        days.map((wd) => {
          const st = statusLabels[wd.status] || { label: wd.status, color: 'default' };
          return (
            <Card key={wd.id} sx={{ mb: 1 }}>
              <CardActionArea onClick={() => navigate(`/summary/${wd.id}`)} sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      {wd.date}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {wd.brigade_name} | Объектов: {wd.sessions_count}
                    </Typography>
                  </Box>
                  <Chip label={st.label} color={st.color} size="small" />
                </Box>
              </CardActionArea>
            </Card>
          );
        })
      )}
    </Box>
  );
}
