import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box, Button, Typography, Alert, Card, CardContent, Fab,
  CircularProgress, List, ListItem, ListItemText, Divider, Chip,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import ExitToAppIcon from '@mui/icons-material/ExitToApp';
import { worksApi } from '../api';

export default function ObjectWorkPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [works, setWorks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadWorks = () => {
    worksApi.bySession(sessionId)
      .then((r) => setWorks(r.data))
      .catch(() => setError('Ошибка загрузки'))
      .finally(() => setLoading(false));
  };

  useEffect(loadWorks, [sessionId]);

  if (loading) return <Box sx={{ textAlign: 'center', mt: 4 }}><CircularProgress /></Box>;

  const totalCost = works.reduce(
    (sum, w) => sum + parseFloat(w.total || 0), 0
  );

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Работы на объекте</Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {works.length > 0 ? (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <List disablePadding>
              {works.map((w) => (
                <Box key={w.id}>
                  <ListItem disablePadding sx={{ py: 1 }}>
                    <ListItemText
                      primary={w.work_name}
                      secondary={`${w.volume} ${w.unit || ''} = ${parseFloat(w.total || 0).toLocaleString('ru-RU')} руб.`}
                    />
                    {w.has_photos ? (
                      <Chip label="Фото" size="small" color="success" />
                    ) : (
                      <Chip label="Нет фото" size="small" color="warning" />
                    )}
                  </ListItem>
                  <Divider />
                </Box>
              ))}
            </List>
            <Typography variant="subtitle1" sx={{ mt: 2, fontWeight: 600 }}>
              Итого: {totalCost.toLocaleString('ru-RU')} руб.
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Typography color="text.secondary" align="center" sx={{ my: 4 }}>
          Работы ещё не добавлены
        </Typography>
      )}

      <Button
        variant="contained"
        color="error"
        startIcon={<ExitToAppIcon />}
        fullWidth
        onClick={() => navigate(`/depart/${sessionId}`)}
        sx={{ mb: 2 }}
      >
        Покинуть объект
      </Button>

      <Fab
        color="primary"
        sx={{ position: 'fixed', bottom: 90, right: 16, zIndex: 1200 }}
        onClick={() => navigate(`/add-work/${sessionId}`)}
      >
        <AddIcon />
      </Fab>
    </Box>
  );
}
