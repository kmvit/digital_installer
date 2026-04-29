import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, Grid, Alert, CircularProgress, LinearProgress,
  Chip, List, ListItem, ListItemText, Divider,
} from '@mui/material';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { dashboardsApi, getApiErrorMessage } from '../api';

const fmtMoney = (s) => Number(s).toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' ₽';
const ZONE_COLORS = { overdue: 'error', at_risk: 'warning' };

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

export default function DashboardPMPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    dashboardsApi.pm()
      .then((r) => setData(r.data))
      .catch((err) => setError(getApiErrorMessage(err, 'Не удалось загрузить дашборд')))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Box sx={{ textAlign: 'center', mt: 8 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!data) return null;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Дашборд РП</Typography>

      <Grid container spacing={1.5} sx={{ mb: 2 }}>
        <Grid item xs={6} md={3}>
          <StatCard title="Мои объекты" value={data.my_objects_count} />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard title="Сейчас на объектах" value={data.active_sessions} />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard title="Проблемных" value={data.problem_zones.length} />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard title="За месяц" value={fmtMoney(data.month_amount)} />
        </Grid>
      </Grid>

      {data.problem_zones.length > 0 && (
        <Card elevation={1} sx={{ mb: 2, borderLeft: 4, borderColor: 'warning.main' }}>
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>
              <WarningAmberIcon sx={{ verticalAlign: 'middle', mr: 1 }} fontSize="small" />
              Проблемные зоны
            </Typography>
            <List dense disablePadding>
              {data.problem_zones.map((z, i) => (
                <Box key={`${z.object_id}-${i}`}>
                  {i > 0 && <Divider />}
                  <ListItem disableGutters button onClick={() => navigate(`/object-progress/${z.object_id}`)}>
                    <ListItemText primary={z.name} secondary={z.message} />
                    <Chip label={z.type === 'overdue' ? 'Просрочено' : 'Риск срыва'} color={ZONE_COLORS[z.type]} size="small" />
                  </ListItem>
                </Box>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      {data.active_locations.length > 0 && (
        <Card elevation={1} sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>Сейчас на моих объектах</Typography>
            <List dense disablePadding>
              {data.active_locations.map((s) => (
                <ListItem key={s.session_id} disableGutters>
                  <ListItemText
                    primary={`${s.brigade} → ${s.object_name}`}
                    secondary={`${Math.floor(s.duration_minutes / 60)}ч ${s.duration_minutes % 60}м · с ${new Date(s.arrived_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`}
                  />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      <Card elevation={1} sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>Прогресс моих объектов</Typography>
          {data.progress.length === 0 ? (
            <Typography variant="body2" color="text.secondary">Нет курируемых объектов.</Typography>
          ) : (
            data.progress.map((o) => {
              const pct = Math.min(100, parseFloat(o.percent));
              return (
                <Box key={o.id} sx={{ mb: 1.5, cursor: 'pointer' }} onClick={() => navigate(`/object-progress/${o.id}`)}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="body2">{o.name}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {o.percent}% · {fmtMoney(o.completed_amount)}
                      {o.deadline && ` · до ${o.deadline}`}
                    </Typography>
                  </Box>
                  <LinearProgress variant="determinate" value={pct} sx={{ height: 6, borderRadius: 3 }} />
                </Box>
              );
            })
          )}
        </CardContent>
      </Card>

      <Card elevation={1} sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>Бригады на моих объектах за месяц</Typography>
          {data.top_brigades.length === 0 ? (
            <Typography variant="body2" color="text.secondary">Нет данных.</Typography>
          ) : (
            <List dense disablePadding>
              {data.top_brigades.map((b, i) => (
                <Box key={b.brigade}>
                  {i > 0 && <Divider />}
                  <ListItem disableGutters>
                    <ListItemText primary={`${i + 1}. ${b.brigade}`} secondary={`${b.workdays} смен · ${b.hours} ч`} />
                    <Chip label={fmtMoney(b.amount)} size="small" color="primary" />
                  </ListItem>
                </Box>
              ))}
            </List>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
