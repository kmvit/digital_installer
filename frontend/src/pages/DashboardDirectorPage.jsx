import { useEffect, useState } from 'react';
import {
  Box, Typography, Card, CardContent, Grid, Alert, CircularProgress,
  List, ListItem, ListItemText, Chip, Divider,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { dashboardsApi, getApiErrorMessage } from '../api';
import LinearProgress from '@mui/material/LinearProgress';

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

const fmtMoney = (s) => Number(s).toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' ₽';

export default function DashboardDirectorPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [planObjects, setPlanObjects] = useState([]);

  useEffect(() => {
    dashboardsApi.director()
      .then((r) => setData(r.data))
      .catch((err) => setError(getApiErrorMessage(err, 'Не удалось загрузить дашборд')))
      .finally(() => setLoading(false));
    dashboardsApi.objectsWithPlans()
      .then((r) => setPlanObjects(r.data || []))
      .catch(() => {});
  }, []);

  if (loading) return <Box sx={{ textAlign: 'center', mt: 8 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!data) return null;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Дашборд директора</Typography>

      <Grid container spacing={1.5} sx={{ mb: 2 }}>
        <Grid item xs={6} md={3}>
          <StatCard title="Сегодня" value={data.today.active_brigades} sub={`Активных бригад · ${data.today.active_sessions} на объектах`} />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard title="Выработка сегодня" value={fmtMoney(data.today.amount)} sub={`${data.today.workdays} смен · ${data.today.hours} ч`} />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard title="За неделю" value={fmtMoney(data.week.amount)} sub={`${data.week.workdays} смен · ${data.week.hours} ч`} />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard title="За месяц" value={fmtMoney(data.month.amount)} sub={`${data.month.workdays} смен · ${data.month.hours} ч`} />
        </Grid>
      </Grid>

      <Card elevation={1} sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle1">Динамика выработки за 7 дней</Typography>
          <MiniChart data={data.week_chart} />
        </CardContent>
      </Card>

      <Card elevation={1} sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>Сейчас на объектах ({data.active_locations.length})</Typography>
          {data.active_locations.length === 0 ? (
            <Typography variant="body2" color="text.secondary">Нет активных сессий.</Typography>
          ) : (
            <List dense disablePadding>
              {data.active_locations.map((s) => (
                <ListItem key={s.session_id} disableGutters>
                  <ListItemText
                    primary={`${s.brigade} → ${s.object_name}`}
                    secondary={`${Math.floor(s.duration_minutes / 60)}ч ${s.duration_minutes % 60}м на объекте · с ${new Date(s.arrived_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`}
                  />
                </ListItem>
              ))}
            </List>
          )}
        </CardContent>
      </Card>

      <Grid container spacing={1.5} sx={{ mb: 2 }}>
        <Grid item xs={12} md={6}>
          <Card elevation={1}>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>Топ бригад за месяц</Typography>
              {data.top_brigades.length === 0 ? (
                <Typography variant="body2" color="text.secondary">Нет данных.</Typography>
              ) : (
                <List dense disablePadding>
                  {data.top_brigades.map((b, i) => (
                    <Box key={b.brigade}>
                      {i > 0 && <Divider />}
                      <ListItem disableGutters>
                        <ListItemText primary={`${i + 1}. ${b.brigade}`} secondary={`${b.hours} ч`} />
                        <Chip label={fmtMoney(b.amount)} size="small" color="primary" />
                      </ListItem>
                    </Box>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card elevation={1}>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>Топ монтажников за месяц</Typography>
              {data.top_workers.length === 0 ? (
                <Typography variant="body2" color="text.secondary">Нет данных.</Typography>
              ) : (
                <List dense disablePadding>
                  {data.top_workers.map((w, i) => (
                    <Box key={w.user}>
                      {i > 0 && <Divider />}
                      <ListItem disableGutters>
                        <ListItemText primary={`${i + 1}. ${w.user}`} secondary={`${w.days} дн.`} />
                        <Chip label={fmtMoney(w.amount)} size="small" color="primary" />
                      </ListItem>
                    </Box>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {planObjects.length > 0 && (
        <Card elevation={1} sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>Прогресс объектов (план/факт)</Typography>
            <List dense disablePadding>
              {planObjects.map((o) => {
                const pct = Math.min(100, parseFloat(o.percent));
                return (
                  <ListItem key={o.id} disableGutters button onClick={() => navigate(`/object-progress/${o.id}`)} sx={{ flexDirection: 'column', alignItems: 'stretch', py: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="body2">{o.name}</Typography>
                      <Typography variant="body2" color="text.secondary">{o.percent}%</Typography>
                    </Box>
                    <LinearProgress variant="determinate" value={pct} sx={{ height: 6, borderRadius: 3 }} />
                  </ListItem>
                );
              })}
            </List>
          </CardContent>
        </Card>
      )}

      {data.overdue_objects.length > 0 && (
        <Card elevation={1} sx={{ mb: 2, borderLeft: 4, borderColor: 'error.main' }}>
          <CardContent>
            <Typography variant="subtitle1" color="error" gutterBottom>
              Просроченные объекты ({data.overdue_objects.length})
            </Typography>
            <List dense disablePadding>
              {data.overdue_objects.map((o) => (
                <ListItem key={o.object_id} disableGutters>
                  <ListItemText
                    primary={o.name}
                    secondary={`Дедлайн ${o.deadline} · просрочено на ${o.days_overdue} дн.`}
                  />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
