import { useState, useEffect, useCallback } from 'react';
import { Chip } from '@mui/material';
import GpsFixedIcon from '@mui/icons-material/GpsFixed';
import GpsOffIcon from '@mui/icons-material/GpsOff';

export function useGps() {
  const [position, setPosition] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const requestPosition = useCallback(() => {
    if (!navigator.geolocation) {
      setError('GPS недоступен');
      return;
    }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setPosition({
          latitude: pos.coords.latitude.toFixed(6),
          longitude: pos.coords.longitude.toFixed(6),
        });
        setLoading(false);
      },
      (err) => {
        setError(err.message);
        setLoading(false);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  }, []);

  useEffect(() => {
    requestPosition();
  }, [requestPosition]);

  return { position, error, loading, requestPosition };
}

export default function GpsStatus({ position, error, loading }) {
  if (loading) return <Chip icon={<GpsFixedIcon />} label="GPS..." size="small" />;
  if (error) return <Chip icon={<GpsOffIcon />} label="GPS выкл" size="small" color="error" />;
  if (position)
    return (
      <Chip
        icon={<GpsFixedIcon />}
        label={`${position.latitude}, ${position.longitude}`}
        size="small"
        color="success"
      />
    );
  return null;
}
