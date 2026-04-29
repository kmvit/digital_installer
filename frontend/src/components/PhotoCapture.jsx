import { useState, useRef } from 'react';
import { Button, Box, Typography, CircularProgress } from '@mui/material';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import DeleteIcon from '@mui/icons-material/Delete';

function getCurrentPositionAsync(timeout = 8000) {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Геолокация не поддерживается'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve(pos),
      (err) => reject(err),
      { enableHighAccuracy: true, timeout, maximumAge: 0 },
    );
  });
}

function loadImage(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}

function formatStamp(capturedAt, latitude, longitude) {
  const dt = new Date(capturedAt);
  const pad = (n) => String(n).padStart(2, '0');
  const ts = `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())} ${pad(dt.getHours())}:${pad(dt.getMinutes())}:${pad(dt.getSeconds())}`;
  const gps = (latitude != null && longitude != null)
    ? `GPS ${Number(latitude).toFixed(6)}, ${Number(longitude).toFixed(6)}`
    : 'GPS: нет данных';
  return [ts, gps];
}

async function stampImage(file, capturedAt, latitude, longitude) {
  const img = await loadImage(file);
  const canvas = document.createElement('canvas');
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(img, 0, 0);

  const lines = formatStamp(capturedAt, latitude, longitude);
  const fontSize = Math.max(18, Math.round(canvas.height / 36));
  const padding = Math.round(fontSize * 0.6);
  ctx.font = `bold ${fontSize}px sans-serif`;
  ctx.textBaseline = 'top';

  const lineHeight = fontSize + 6;
  const widths = lines.map((l) => ctx.measureText(l).width);
  const boxWidth = Math.max(...widths) + padding * 2;
  const boxHeight = lineHeight * lines.length + padding * 2 - 6;
  const x = padding;
  const y = canvas.height - boxHeight - padding;

  ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
  ctx.fillRect(x, y, boxWidth, boxHeight);

  ctx.fillStyle = '#ffffff';
  lines.forEach((line, i) => {
    ctx.fillText(line, x + padding, y + padding + i * lineHeight);
  });

  const blob = await new Promise((resolve) =>
    canvas.toBlob(resolve, 'image/jpeg', 0.92)
  );
  URL.revokeObjectURL(img.src);
  const stampedName = (file.name || 'photo.jpg').replace(/\.[^.]+$/, '') + '.jpg';
  return new File([blob], stampedName, { type: 'image/jpeg', lastModified: Date.now() });
}

export default function PhotoCapture({ onPhoto, label = 'Сделать фото', required = false, inputId = 'photo-capture' }) {
  const [preview, setPreview] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef();

  const handleCapture = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError('');
    setProcessing(true);
    try {
      const bypassGps = String(import.meta.env.VITE_BYPASS_GPS || '').toLowerCase() === '1'
        || String(import.meta.env.VITE_BYPASS_GPS || '').toLowerCase() === 'true';
      let pos = null;
      try {
        pos = await getCurrentPositionAsync();
      } catch (err) {
        if (!bypassGps) {
          setError('Не удалось получить GPS — разрешите геолокацию и повторите.');
          setProcessing(false);
          if (inputRef.current) inputRef.current.value = '';
          return;
        }
        // тестовый режим — пропускаем без GPS
      }

      const capturedAt = new Date().toISOString();
      const latitude = pos ? pos.coords.latitude : null;
      const longitude = pos ? pos.coords.longitude : null;

      const stamped = await stampImage(file, capturedAt, latitude, longitude);

      setPreview(URL.createObjectURL(stamped));
      onPhoto(stamped, { captured_at: capturedAt, latitude, longitude });
    } catch (err) {
      setError('Ошибка обработки фото: ' + (err.message || err));
    } finally {
      setProcessing(false);
    }
  };

  const handleRemove = () => {
    setPreview(null);
    setError('');
    onPhoto(null, null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <Box>
      <input ref={inputRef} type="file" accept="image/*" capture="environment" onChange={handleCapture} style={{ display: 'none' }} id={inputId} />

      {!preview ? (
        <label htmlFor={inputId}>
          <Button variant="outlined" component="span" startIcon={processing ? <CircularProgress size={20} /> : <CameraAltIcon sx={{ fontSize: 32 }} />} fullWidth disabled={processing} sx={{ py: 3, borderStyle: 'dashed', fontSize: '1.15rem' }}>
            {processing ? 'Обработка…' : label} {required && !processing && '*'}
          </Button>
        </label>
      ) : (
        <Box>
          <Box component="img" src={preview} alt="Фото" sx={{ width: '100%', maxHeight: 300, objectFit: 'cover', borderRadius: 2, mb: 1 }} />
          <Button size="small" color="error" startIcon={<DeleteIcon />} onClick={handleRemove}>
            Удалить
          </Button>
        </Box>
      )}

      {error && (
        <Typography variant="caption" color="error" display="block" sx={{ mt: 0.5 }}>{error}</Typography>
      )}
      {required && !preview && !error && (
        <Typography variant="caption" color="error">Фото обязательно</Typography>
      )}
    </Box>
  );
}
