import { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Chip,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { reportsApi, getApiErrorMessage } from '../api';

const REPORT_TYPES = [
  { id: 'timesheet', label: 'Табель' },
  { id: 'piecework', label: 'Сдельная ведомость' },
  { id: 'completion_act', label: 'Акт выполненных работ' },
  { id: 'equipment_act', label: 'Акт по инструменту' },
];

const COLUMNS_BY_REPORT = {
  timesheet: [
    { key: 'date', label: 'Дата' },
    { key: 'brigade', label: 'Бригада', minWidth: 130 },
    { key: 'foreman', label: 'Бригадир' },
    { key: 'workers', label: 'Состав', minWidth: 220 },
    { key: 'clock_in_at', label: 'Начало' },
    { key: 'clock_out_at', label: 'Конец' },
    { key: 'hours', label: 'Часы' },
    { key: 'overtime_hours', label: 'Переработка' },
    { key: 'status', label: 'Статус' },
  ],
  piecework: [
    { key: 'date', label: 'Дата' },
    { key: 'brigade', label: 'Бригада', minWidth: 130 },
    { key: 'object', label: 'Объект', minWidth: 220 },
    { key: 'work_name', label: 'Работа', minWidth: 260 },
    { key: 'volume', label: 'Объём' },
    { key: 'unit', label: 'Ед.' },
    { key: 'rate', label: 'Расценка' },
    { key: 'amount', label: 'Сумма' },
  ],
  completion_act: [
    { key: 'object', label: 'Объект', minWidth: 240 },
    { key: 'work_name', label: 'Работа', minWidth: 280 },
    { key: 'volume', label: 'Объём' },
    { key: 'unit', label: 'Ед.' },
    { key: 'rate', label: 'Расценка' },
    { key: 'amount', label: 'Сумма' },
  ],
  equipment_act: [
    { key: 'date', label: 'Дата' },
    { key: 'brigade', label: 'Бригада', minWidth: 130 },
    { key: 'item_name', label: 'Инструмент', minWidth: 220 },
    { key: 'morning_status', label: 'Утро' },
    { key: 'evening_status', label: 'Вечер' },
    { key: 'is_mismatch', label: 'Совпадение' },
  ],
};

function formatCellValue(key, value) {
  if (value === null || value === undefined || value === '') return '—';
  if (Array.isArray(value)) return value.join(', ');
  if (key === 'is_mismatch') return value ? 'Нет' : 'Да';
  if (typeof value === 'string' && value.includes('T')) {
    const date = new Date(value);
    if (!Number.isNaN(date.getTime())) return date.toLocaleString('ru-RU');
  }
  return String(value);
}

export default function ReportsPage() {
  const [reportType, setReportType] = useState('timesheet');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [brigadeId, setBrigadeId] = useState('');
  const [objectId, setObjectId] = useState('');
  const [rows, setRows] = useState([]);
  const [meta, setMeta] = useState({});
  const [loading, setLoading] = useState(false);
  const [filtersLoading, setFiltersLoading] = useState(true);
  const [brigades, setBrigades] = useState([]);
  const [objects, setObjects] = useState([]);
  const [error, setError] = useState('');

  const params = {
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    brigade: brigadeId || undefined,
    object: objectId || undefined,
  };

  const loadReport = async () => {
    setLoading(true);
    setError('');
    try {
      let response;
      if (reportType === 'timesheet') response = await reportsApi.timesheet(params);
      if (reportType === 'piecework') response = await reportsApi.piecework(params);
      if (reportType === 'completion_act') response = await reportsApi.completionAct(params);
      if (reportType === 'equipment_act') response = await reportsApi.equipmentAct(params);

      setRows(response?.data?.rows || []);
      setMeta({
        total_amount: response?.data?.total_amount,
        mismatch_count: response?.data?.mismatch_count,
      });
    } catch (err) {
      setError(getApiErrorMessage(err, 'Не удалось загрузить отчёт'));
      setRows([]);
      setMeta({});
    } finally {
      setLoading(false);
    }
  };

  const download = async (format) => {
    setError('');
    try {
      const { data } = await reportsApi.exportReport(format, {
        ...params,
        report: reportType,
      });
      const reportName = REPORT_TYPES.find((r) => r.id === reportType)?.id || 'report';
      const ext = format === 'xlsx' ? 'csv' : 'pdf';
      const blobUrl = URL.createObjectURL(data);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = `${reportName}.${ext}`;
      link.click();
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Не удалось скачать файл отчёта'));
    }
  };

  const columns = COLUMNS_BY_REPORT[reportType] || [];

  useEffect(() => {
    reportsApi.filters()
      .then((r) => {
        setBrigades(r.data?.brigades || []);
        setObjects(r.data?.objects || []);
      })
      .catch(() => {
        // Не блокируем страницу отчётов, даже если справочники фильтров временно недоступны.
      })
      .finally(() => setFiltersLoading(false));
  }, []);

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Отчёты</Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Stack spacing={1.5}>
            <Select value={reportType} onChange={(e) => setReportType(e.target.value)} size="small">
              {REPORT_TYPES.map((r) => (
                <MenuItem key={r.id} value={r.id}>{r.label}</MenuItem>
              ))}
            </Select>
            <Stack direction="row" spacing={1}>
              <Box sx={{ flex: 1 }}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                  Дата от
                </Typography>
                <TextField
                  type="date"
                  value={dateFrom}
                  size="small"
                  onChange={(e) => setDateFrom(e.target.value)}
                  fullWidth
                />
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                  Дата до
                </Typography>
                <TextField
                  type="date"
                  value={dateTo}
                  size="small"
                  onChange={(e) => setDateTo(e.target.value)}
                  fullWidth
                />
              </Box>
            </Stack>
            <Stack direction="row" spacing={1}>
              <Select
                value={brigadeId}
                onChange={(e) => setBrigadeId(e.target.value)}
                size="small"
                fullWidth
                displayEmpty
                disabled={filtersLoading}
              >
                <MenuItem value="">Все бригады</MenuItem>
                {brigades.map((b) => (
                  <MenuItem key={b.id} value={String(b.id)}>{b.name}</MenuItem>
                ))}
              </Select>
              <Select
                value={objectId}
                onChange={(e) => setObjectId(e.target.value)}
                size="small"
                fullWidth
                displayEmpty
                disabled={filtersLoading}
              >
                <MenuItem value="">Все объекты</MenuItem>
                {objects.map((obj) => (
                  <MenuItem key={obj.id} value={String(obj.id)}>{obj.name}</MenuItem>
                ))}
              </Select>
            </Stack>
            <Button variant="contained" onClick={loadReport} disabled={loading}>
              {loading ? <CircularProgress size={22} /> : 'Сформировать'}
            </Button>
            <Stack direction="row" spacing={1}>
              <Button variant="outlined" onClick={() => download('xlsx')}>Экспорт Excel</Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>Результат</Typography>
          {meta.total_amount && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Сумма: {meta.total_amount}
            </Typography>
          )}
          {meta.mismatch_count !== undefined && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Несовпадений по инструменту: {meta.mismatch_count}
            </Typography>
          )}
          {rows.length === 0 ? (
            <Typography color="text.secondary">Нет данных. Нажмите "Сформировать".</Typography>
          ) : (
            <TableContainer
              sx={{
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 1,
                overflowX: 'auto',
              }}
            >
              <Table size="small" sx={{ minWidth: 980, tableLayout: 'auto' }}>
                <TableHead>
                  <TableRow>
                    {columns.map((column) => (
                      <TableCell
                        key={column.key}
                        sx={{
                          minWidth: column.minWidth || 100,
                          whiteSpace: 'nowrap',
                          fontWeight: 600,
                        }}
                      >
                        {column.label}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rows.map((row, idx) => (
                    <TableRow key={`${row.workday_id || row.item_name || 'row'}-${idx}`} hover>
                      {columns.map((column) => (
                        <TableCell
                          key={`${column.key}-${idx}`}
                          sx={{
                            minWidth: column.minWidth || 100,
                            verticalAlign: 'top',
                          }}
                        >
                          {column.key === 'is_mismatch' ? (
                            <Chip
                              size="small"
                              color={row.is_mismatch ? 'warning' : 'success'}
                              label={row.is_mismatch ? 'Есть расхождение' : 'ОК'}
                            />
                          ) : (
                            formatCellValue(column.key, row[column.key])
                          )}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
