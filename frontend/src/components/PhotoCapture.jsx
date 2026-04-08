import { useState, useRef } from 'react';
import { Button, Box, Typography } from '@mui/material';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import DeleteIcon from '@mui/icons-material/Delete';

export default function PhotoCapture({ onPhoto, label = 'Сделать фото', required = false }) {
  const [preview, setPreview] = useState(null);
  const inputRef = useRef();

  const handleCapture = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPreview(URL.createObjectURL(file));
    onPhoto(file);
  };

  const handleRemove = () => {
    setPreview(null);
    onPhoto(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <Box sx={{ my: 2 }}>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleCapture}
        style={{ display: 'none' }}
        id="photo-capture"
      />

      {!preview ? (
        <label htmlFor="photo-capture">
          <Button
            variant="outlined"
            component="span"
            startIcon={<CameraAltIcon />}
            fullWidth
            color={required ? 'primary' : 'inherit'}
            sx={{ py: 2 }}
          >
            {label} {required && '*'}
          </Button>
        </label>
      ) : (
        <Box>
          <Box
            component="img"
            src={preview}
            alt="Фото"
            sx={{
              width: '100%',
              maxHeight: 300,
              objectFit: 'cover',
              borderRadius: 2,
              mb: 1,
            }}
          />
          <Button
            size="small"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={handleRemove}
          >
            Удалить фото
          </Button>
        </Box>
      )}

      {required && !preview && (
        <Typography variant="caption" color="error">
          Фото обязательно
        </Typography>
      )}
    </Box>
  );
}
