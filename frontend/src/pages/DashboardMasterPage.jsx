import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, Grid, Alert, CircularProgress,
  Chip, Button,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HighlightOffIcon from '@mui/icons-material/HighlightOff';
import { dashboardsApi, getApiErrorMessage } from '../api';

const fmtMoney = (s) => Number(s).toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' ₽';

function StatCard({ title, value, sub }) {
  return (
    <Card elevation={1}>
      <CardContent>
        <Typography variant="caption" color="text.secondary">{title}</Typography>
        <Typography variant="h5" sx={{ fontWeight: 700, my: 0.5 }}>{value}</Typography>
        {sub && <Typography variant="body2" color="text.secondary">{sub}</Typography>}
      </CardContent>
    </Card>
  );
}

function MiniChart({ data }) {
  if (!data || data.length === 0) return null;
  const values = data.map((d) => parseFloat(d.amount) || 0);
  const max = Math.max(...values, 1);
  return (
    <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 1, height: 100, mt: 1 }}>
      {data.map((d) => {
        const v = parseFloat(d.amount) || 0;
        const h = Math.max(2, (v / max) * 100);
        return (
          <Box key={d.date} sx={{ flex: 1, textAlign: 'center' }}>
            <Box sx={{ height: `${h}%`, bgcolor: 'primary.main', borderRadius: 1, minHeight: 2 }} />
            <Typography variant="caption" sx={{ display: 'block', mt: 0.5, fontSize: 10 }}>
              {d.date.slice(5)}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}

export default function DashboardMasterPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    dashboardsApi.master()
      .then((r) => setData(r.data))
      .catch((err) => setError(getApiErrorMessage(err, 'Не удалось загрузить дашборд')))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Box sx={{ textAlign: 'center', mt: 8 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!data) return null;

  const t = data.today;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Моя бригада</Typography>
      <Card elevation={2} sx={{ mb: 2, bgcolor: 'primary.main', color: 'white' }}>
        <CardContent>
          <Typography variant="h6">{data.brigade.name}</Typography>
          <Typography variant="body2" sx={{ opacity: 0.85 }}>
            Состав: {data.brigade.members_count} чел.
          </Typography>
        </CardContent>
      </Card>

      <Grid container spacing={1.5} sx={{ mb: 2 }}>
        <Grid item xs={6}>
          <StatCard
            title="Сегодня"
            value={t ? fmtMoney(t.amount) : '—'}
            sub={t ? `${t.completed_works} работ · ${t.hours} ч · ${t.sessions} объектов` : 'Смена не открыта'}
          />
        </Grid>
        <Grid item xs={6}>
          <StatCard
            title="Месяц"
            value={fmtMoney(data.month.amount)}
            sub={`${data.month.workdays} смен · ${data.month.hours} ч`}
          />
        </Grid>
      </Grid>

      <Card elevation={1} sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle1">Выработка за 7 дней</Typography>
          <MiniChart data={data.week_chart} />
        </CardContent>
      </Card>

      {data.current_session && (
        <Card elevation={1} sx={{ mb: 2, borderLeft: 4, borderColor: 'success.main' }}>
          <CardContent>
            <Typography variant="caption" color="text.secondary">Сейчас на объекте</Typography>
            <Typography variant="subtitle1">{data.current_session.object_name}</Typography>
            <Typography variant="body2" color="text.secondary">
              С {new Date(data.current_session.arrived_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
            </Typography>
            <Button
              size="small" sx={{ mt: 1 }}
              onClick={() => navigate(`/object/${data.current_session.session_id}`)}
            >
              К объекту
            </Button>
          </CardContent>
        </Card>
      )}

      <Card elevation={1} sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>Назначения</Typography>
          <Typography variant="body2" color="text.secondary">
            Активных назначений в работе: <b>{data.active_assignments}</b>
          </Typography>
          <Button size="small" sx={{ mt: 1 }} onClick={() => navigate('/my-assignments')}>
            Открыть «Мои работы»
          </Button>
        </CardContent>
      </Card>

      <Card elevation={1} sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>Чек-листы оборудования</Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip
              icon={data.checklists_today.morning ? <CheckCircleIcon /> : <HighlightOffIcon />}
              label="Утренний"
              color={data.checklists_today.morning ? 'success' : 'default'}
              variant={data.checklists_today.morning ? 'filled' : 'outlined'}
            />
            <Chip
              icon={data.checklists_today.evening ? <CheckCircleIcon /> : <HighlightOffIcon />}
              label="Вечерний"
              color={data.checklists_today.evening ? 'success' : 'default'}
              variant={data.checklists_today.evening ? 'filled' : 'outlined'}
            />
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
