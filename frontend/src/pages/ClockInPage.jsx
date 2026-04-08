import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Typography, Alert, Checkbox, FormControlLabel,
  List, ListItem, CircularProgress,
} from '@mui/material';
import PhotoCapture from '../components/PhotoCapture';
import GpsStatus, { useGps } from '../components/GpsStatus';
import { workdayApi, mobileApi } from '../api';

export default function ClockInPage() {
  const navigate = useNavigate();
  const { position, error: gpsError, loading: gpsLoading } = useGps();
  const [photo, setPhoto] = useState(null);
  const [members, setMembers] = useState([]);
  const [selected, setSelected] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    mobileApi.myBrigade()
      .then((r) => setMembers(r.data.members || []))
      .catch(() => {});
  }, []);

  const toggleMember = (id) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleSubmit = async () => {
    if (!photo) {
      setError('Фото обязательно для начала смены');
      return;
    }
    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('photo', photo);
    if (position) {
      formData.append('latitude', position.latitude);
      formData.append('longitude', position.longitude);
    }
    selected.forEach((id) => formData.append('workers_present', id));

    try {
      await workdayApi.clockIn(formData);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка при открытии смены');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Начало смены</Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Box sx={{ mb: 2 }}>
        <GpsStatus position={position} error={gpsError} loading={gpsLoading} />
      </Box>

      <PhotoCapture onPhoto={setPhoto} label="Фото бригады" required />

      {members.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Отметить присутствующих
          </Typography>
          <List>
            {members.map((m) => (
              <ListItem key={m.id} disablePadding>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={selected.includes(m.id)}
                      onChange={() => toggleMember(m.id)}
                    />
                  }
                  label={m.first_name && m.last_name
                    ? `${m.last_name} ${m.first_name}`
                    : m.username}
                />
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      <Button
        variant="contained"
        size="large"
        fullWidth
        onClick={handleSubmit}
        disabled={loading || !photo}
        sx={{ mt: 3 }}
      >
        {loading ? <CircularProgress size={24} /> : 'Начать смену'}
      </Button>
    </Box>
  );
}
