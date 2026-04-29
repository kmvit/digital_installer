import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, Alert, CircularProgress, LinearProgress,
  Chip, Grid, Button,
} from '@mui/material';
import { dashboardsApi, getApiErrorMessage } from '../api';

const RISK_COLORS = { green: 'success', yellow: 'warning', red: 'error' };
const RISK_LABELS = { green: 'В графике', yellow: 'Риск', red: 'Просрочено' };
const fmtMoney = (s) => Number(s).toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' ₽';

function SCurve({ data }) {
  if (!data || data.length < 2) return <Typography variant="caption" color="text.secondary">Недостаточно данных для графика.</Typography>;
  const W = 600, H = 200, P = 30;
  const dates = data.map((d) => new Date(d.date).getTime());
  const minD = Math.min(...dates), maxD = Math.max(...dates);
  const values = data.flatMap((d) => [parseFloat(d.planned), parseFloat(d.actual)]);
  const maxV = Math.max(...values, 1);
  const x = (t) => P + ((t - minD) / Math.max(1, maxD - minD)) * (W - 2 * P);
  const y = (v) => H - P - (v / maxV) * (H - 2 * P);
  const pathFor = (key) => data.map((d, i) => {
    const px = x(new Date(d.date).getTime());
    const py = y(parseFloat(d[key]));
    return `${i === 0 ? 'M' : 'L'} ${px.toFixed(1)} ${py.toFixed(1)}`;
  }).join(' ');
  return (
    <Box sx={{ width: '100%', overflow: 'auto' }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', minWidth: 360, height: H }}>
        <line x1={P} y1={H - P} x2={W - P} y2={H - P} stroke="#999" />
        <line x1={P} y1={P} x2={P} y2={H - P} stroke="#999" />
        <path d={pathFor('planned')} stroke="#3f51b5" strokeWidth="2" fill="none" strokeDasharray="4 4" />
        <path d={pathFor('actual')} stroke="#2e7d32" strokeWidth="2.5" fill="none" />
        <text x={P} y={P - 8} fontSize="11" fill="#3f51b5">— — план</text>
        <text x={P + 90} y={P - 8} fontSize="11" fill="#2e7d32">—— факт</text>
        <text x={P} y={H - 8} fontSize="10" fill="#666">{data[0].date}</text>
        <text x={W - P - 60} y={H - 8} fontSize="10" fill="#666">{data[data.length - 1].date}</text>
      </svg>
    </Box>
  );
}

export default function ObjectProgressPage() {
  const { objectId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    dashboardsApi.objectProgress(objectId)
      .then((r) => setData(r.data))
      .catch((err) => setError(getApiErrorMessage(err, 'Не удалось загрузить прогресс')))
      .finally(() => setLoading(false));
  }, [objectId]);

  if (loading) return <Box sx={{ textAlign: 'center', mt: 8 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!data) return null;

  return (
    <Box>
      <Button size="small" onClick={() => navigate(-1)}>← Назад</Button>
      <Typography variant="h5" sx={{ mt: 1 }} gutterBottom>{data.object.name}</Typography>
      {data.object.deadline && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Дедлайн: {data.object.deadline}
        </Typography>
      )}

      <Grid container spacing={1.5} sx={{ mb: 2 }}>
        <Grid item xs={6} md={4}>
          <Card elevation={1}>
            <CardContent>
              <Typography variant="caption" color="text.secondary">План</Typography>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>{fmtMoney(data.totals.planned_amount)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={4}>
          <Card elevation={1}>
            <CardContent>
              <Typography variant="caption" color="text.secondary">Факт</Typography>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>{fmtMoney(data.totals.completed_amount)}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card elevation={1}>
            <CardContent>
              <Typography variant="caption" color="text.secondary">Прогресс</Typography>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>{data.totals.percent}%</Typography>
              <LinearProgress variant="determinate" value={Math.min(100, parseFloat(data.totals.percent))} sx={{ mt: 1, height: 8, borderRadius: 4 }} />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card elevation={1} sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>S-кривая (план vs факт, нарастающим итогом)</Typography>
          <SCurve data={data.s_curve} />
        </CardContent>
      </Card>

      <Typography variant="subtitle1" sx={{ mb: 1 }}>По видам работ ({data.plans.length})</Typography>
      {data.plans.length === 0 && (
        <Card elevation={0} sx={{ py: 4, textAlign: 'center', bgcolor: 'grey.50' }}>
          <Typography color="text.secondary">План для объекта не задан. Заполните «Плановые объёмы работ» в админке объекта.</Typography>
        </Card>
      )}
      {data.plans.map((p) => {
        const pct = Math.min(100, parseFloat(p.percent));
        return (
          <Card key={p.plan_id} elevation={1} sx={{ mb: 1.5 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="subtitle2" sx={{ flex: 1, mr: 1 }}>{p.work_type_name}</Typography>
                <Chip label={RISK_LABELS[p.risk]} size="small" color={RISK_COLORS[p.risk]} />
              </Box>
              <Typography variant="body2" color="text.secondary">
                {p.completed_volume} / {p.planned_volume} ({p.percent}%)
                {' · '}
                Сумма: {fmtMoney(p.completed_amount)} / {fmtMoney(p.planned_amount)}
              </Typography>
              <LinearProgress
                variant="determinate"
                value={pct}
                color={RISK_COLORS[p.risk]}
                sx={{ mt: 1, height: 8, borderRadius: 4 }}
              />
              {(p.planned_start || p.planned_end || p.forecast_end) && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                  {p.planned_start && `Старт: ${p.planned_start}`}
                  {p.planned_end && ` · Завершение: ${p.planned_end}`}
                  {p.forecast_end && ` · Прогноз: ${p.forecast_end}`}
                </Typography>
              )}
              {(parseFloat(p.required_daily) > 0 || parseFloat(p.historical_daily) > 0) && (
                <Box sx={{ display: 'flex', gap: 1, mt: 0.5, flexWrap: 'wrap' }}>
                  <Chip
                    size="small"
                    label={`Нужно/день: ${p.required_daily}`}
                    color={RISK_COLORS[p.risk_required] || 'default'}
                    variant="outlined"
                  />
                  <Chip
                    size="small"
                    label={`Средняя/день: ${p.historical_daily}`}
                    variant="outlined"
                  />
                  {p.risk_required === 'red' && (
                    <Chip size="small" color="error" label="⚠ Риск срыва сроков" />
                  )}
                </Box>
              )}
              {p.notes && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                  {p.notes}
                </Typography>
              )}
            </CardContent>
          </Card>
        );
      })}
    </Box>
  );
}
