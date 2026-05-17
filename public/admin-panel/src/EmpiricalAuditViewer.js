// src/EmpiricalAuditViewer.js
import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box, Typography, Button, Paper, Table,
  TableBody, TableCell, TableContainer, TableHead, TableRow,
  CircularProgress, Switch, FormControlLabel, Chip, Tooltip,
  Tabs, Tab, List, ListItem, ListItemText, ListItemSecondaryAction, IconButton, Divider,
  Alert
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import HistoryIcon from '@mui/icons-material/History';
import DescriptionIcon from '@mui/icons-material/Description';
import VisibilityIcon from '@mui/icons-material/Visibility';
import SettingsSuggestIcon from '@mui/icons-material/SettingsSuggest';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import { getAuth } from 'firebase/auth';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';
const POLL_INTERVAL_MS = 3000;

// ── Export to CSV ────────────────────────────────────────────────────────────
function exportToCSV(results, indicatorsMap, filename) {
  const getRazonamientoText = (raz) => {
    if (!raz) return '';
    if (typeof raz === 'string') return raz;
    if (typeof raz === 'object') {
      const parts = [];
      if (raz.comparativa_normativa) parts.push(`Comparativa: ${raz.comparativa_normativa}`);
      if (raz.ubicacion_contextual) parts.push(`Ubicación: ${raz.ubicacion_contextual}`);
      if (raz.justificacion_vacios) parts.push(`Vacíos: ${raz.justificacion_vacios}`);
      return parts.join(' | ');
    }
    return String(raz);
  };

  const headers = ['ID', 'Referencia ESRS', 'Indicador', 'Evidencia Encontrada', 'Página', 'Cita Literal', 'Razonamiento Técnico', 'Validación'];
  const rows = Object.values(results)
    .sort((a, b) => Number(a.indicator_id) - Number(b.indicator_id))
    .map((row) => {
      const ind = indicatorsMap[row.indicator_id] || {};
      const razonamientoText = getRazonamientoText(row.razonamiento);
      return [
        row.indicator_id,
        ind.ref || '',
        ind.question || '',
        row.cumple || '',
        row.pagina_real || '',
        (row.evidencia_literal || '').replace(/\n/g, ' '),
        razonamientoText.replace(/\n/g, ' '),
        row.human_validation === true ? 'Validado' : 'Pendiente',
      ].map((cell) => `"${String(cell).replace(/"/g, '""')}"`);
    });

  const csvContent = [headers.map((h) => `"${h}"`), ...rows].map((r) => r.join(',')).join('\n');
  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

// ── Chip de color para el estado de evidencia ────────────────────────────────
function EvidenciaChip({ value }) {
  const normalized = (value || '').toUpperCase().replace('Í', 'I');
  const map = {
    'SÍ': { label: 'EVIDENCIA', color: 'success' },
    'SI': { label: 'EVIDENCIA', color: 'success' },
    'NO': { label: 'NO ENCONTRADO', color: 'error' },
    'NA': { label: 'N/A', color: 'default' },
    'FE': { label: 'DOC. EXTERNO',  color: 'warning' },
    'ERROR': { label: 'ERROR', color: 'error' },
  };
  const cfg = map[normalized] || { label: value, color: 'default' };
  return <Chip label={cfg.label} color={cfg.color} size="small" sx={{ fontWeight: 'bold' }} />;
}

// ── Componente principal ─────────────────────────────────────────────────────
export default function EmpiricalAuditViewer() {
  const [file, setFile] = useState(null);
  const [indicatorsFile, setIndicatorsFile] = useState(null);
  const [threadId, setThreadId] = useState('');
  const [auditData, setAuditData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [tabValue, setTabValue] = useState(0);
  
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  
  const [indicators, setIndicators] = useState([]);
  const [indicatorsMap, setIndicatorsMap] = useState({});
  const [loadingIndicators, setLoadingIndicators] = useState(false);
  const [uploadingIndicators, setUploadingIndicators] = useState(false);
  const [isCacheSyncing, setIsCacheSyncing] = useState(false);
  
  const pollRef = useRef(null);

  const fetchHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const auth = getAuth();
      const token = await auth.currentUser?.getIdToken();
      const resp = await fetch(`${API_URL}/api/audit/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const body = await resp.json();
      if (body.ok) setHistory(body.data);
    } catch (err) {
      console.error('Error cargando historial:', err);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  const fetchIndicators = useCallback(async () => {
    setLoadingIndicators(true);
    try {
      const auth = getAuth();
      const token = await auth.currentUser?.getIdToken();
      const resp = await fetch(`${API_URL}/api/indicators`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const body = await resp.json();
      if (body.ok && body.data && body.data.indicators) {
        setIndicators(body.data.indicators);
        const map = {};
        body.data.indicators.forEach(ind => { map[ind.id] = ind; });
        setIndicatorsMap(map);
      }
    } catch (err) {
      console.error('Error cargando indicadores:', err);
    } finally {
      setLoadingIndicators(false);
    }
  }, []);

  useEffect(() => {
    fetchIndicators();
  }, [fetchIndicators]);

  useEffect(() => {
    if (tabValue === 1) fetchHistory();
    if (tabValue === 2) fetchIndicators();
  }, [tabValue, fetchHistory, fetchIndicators]);

  const fetchAuditStatus = useCallback(async (id) => {
    try {
      const resp = await fetch(`${API_URL}/api/audit/empirical/${id}`);
      if (!resp.ok) return;
      const body = await resp.json();
      if (body.ok && body.data) {
        setAuditData(body.data);
        if (body.data.indicadores_utilizados_snapshot) {
           const map = {};
           body.data.indicadores_utilizados_snapshot.forEach(ind => { map[ind.id] = ind; });
           setIndicatorsMap(map);
        }
        
        if (body.data.status === 'completed' || body.data.status === 'error') {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }
    } catch (err) {
      console.error('Error en polling:', err);
    }
  }, []);

  useEffect(() => {
    if (!threadId) return;
    fetchAuditStatus(threadId);
    pollRef.current = setInterval(() => fetchAuditStatus(threadId), POLL_INTERVAL_MS);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [threadId, fetchAuditStatus]);

  const handleLaunchAudit = async () => {
    if (!file) { setError('Por favor, selecciona un archivo PDF.'); return; }
    setError(''); setLoading(true); setAuditData(null); setThreadId('');
    try {
      const auth = getAuth();
      if (!auth.currentUser) throw new Error('Usuario no autenticado.');
      const token = await auth.currentUser.getIdToken();
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch(`${API_URL}/api/audit/empirical`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!response.ok) throw new Error('Error al iniciar el análisis');
      const data = await response.json();
      setThreadId(data.thread_id);
      setTabValue(0);
    } catch (err) {
      console.error(err); setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadIndicators = async () => {
    if (!indicatorsFile) { setError('Por favor, selecciona un archivo Excel o CSV.'); return; }
    setError(''); setUploadingIndicators(true); setIsCacheSyncing(true);
    try {
      const auth = getAuth();
      if (!auth.currentUser) throw new Error('Usuario no autenticado.');
      const token = await auth.currentUser.getIdToken();
      const formData = new FormData();
      formData.append('file', indicatorsFile);
      const response = await fetch(`${API_URL}/api/indicators/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const body = await response.json();
      if (!response.ok) {
        const errorMsg = body.error?.message || (typeof body.error === 'string' ? body.error : 'Error al subir la matriz');
        throw new Error(errorMsg);
      }
      
      await fetchIndicators();
      setIndicatorsFile(null);
      setTimeout(() => setIsCacheSyncing(false), 5000); 
    } catch (err) {
      console.error(err); setError(err.message);
      setIsCacheSyncing(false);
    } finally {
      setUploadingIndicators(false);
    }
  };

  const handleFeedbackToggle = async (indicatorId, currentValue) => {
    if (!threadId || !auditData) return;
    setAuditData((prev) => ({
      ...prev,
      results: { ...prev.results, [indicatorId]: { ...prev.results[indicatorId], human_validation: !currentValue } },
    }));
    try {
      const auth = getAuth();
      const token = await auth.currentUser?.getIdToken();
      await fetch(`${API_URL}/api/audit/empirical/${threadId}/feedback`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ indicator_id: indicatorId, human_validation: !currentValue }),
      });
    } catch (err) { console.error('Error al guardar validación:', err); }
  };

  const results = auditData?.results || {};
  const isCompleted = auditData?.status === 'completed';
  const isProcessing = auditData?.status === 'processing' || (threadId && !auditData);
  const completedCount = Object.keys(results).length;
  const totalIndicators = auditData?.indicadores_utilizados_snapshot?.length || indicators.length;
  const exportFilename = `analisis_evidencias_${auditData?.filename?.replace('.pdf','') || 'informe'}_${new Date().toISOString().slice(0,10)}.csv`;

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom fontWeight="black" color="primary.main">
        RECAVA Analizador AI
      </Typography>

      <Paper sx={{ mb: 3, borderRadius: 3, overflow: 'hidden' }} elevation={4}>
        <Tabs 
          value={tabValue} 
          onChange={(e, v) => setTabValue(v)} 
          indicatorColor="primary" 
          textColor="primary"
          variant="fullWidth"
          sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'grey.50' }}
        >
          <Tab icon={<DescriptionIcon />} label="Analizar Documento" />
          <Tab icon={<HistoryIcon />} label="Historial de Análisis" />
          <Tab icon={<SettingsSuggestIcon />} label="Configurar Indicadores" />
        </Tabs>
        
        <Box sx={{ p: 4 }}>
          {/* ── PESTAÑA 0: Analizar Documento ── */}
          {tabValue === 0 && (
            <Box>
              <Typography variant="h6" gutterBottom fontWeight="bold">Búsqueda de Evidencias en PDF</Typography>
              <Typography variant="body2" color="text.secondary" mb={3}>
                El análisis se ejecutará buscando evidencias para los {indicators.length} indicadores activos de su configuración.
              </Typography>
              
              {isCacheSyncing && (
                <Alert severity="info" sx={{ mb: 3, borderRadius: 2 }}>
                  Sincronizando base normativa (RAG)... Preparando el motor de búsqueda.
                </Alert>
              )}

              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                <Button variant="outlined" component="label" sx={{ height: 64, flexGrow: 1, borderRadius: 3, borderStyle: 'dashed', borderWidth: 2 }}>
                  {file ? file.name : 'Seleccionar Informe PDF'}
                  <input type="file" hidden accept="application/pdf" onChange={(e) => setFile(e.target.files[0])} />
                </Button>
                <Button 
                  variant="contained" 
                  onClick={handleLaunchAudit} 
                  disabled={loading || !file || isCacheSyncing} 
                  sx={{ height: 64, px: 6, borderRadius: 3, fontWeight: 'black', fontSize: '1.1rem', boxShadow: 6 }}
                >
                  {loading ? <CircularProgress size={28} color="inherit" /> : 'Analizar documento'}
                </Button>
              </Box>
              {error && <Typography color="error" sx={{ mt: 2, fontWeight: 'medium' }}>{error}</Typography>}
            </Box>
          )}

          {/* ── PESTAÑA 1: Historial ── */}
          {tabValue === 1 && (
            <Box>
              <Typography variant="h6" gutterBottom fontWeight="bold">Análisis Realizados</Typography>
              {loadingHistory ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}><CircularProgress /></Box>
              ) : history.length === 0 ? (
                <Typography color="text.secondary" align="center" sx={{ py: 3 }}>No se han realizado análisis previos.</Typography>
              ) : (
                <List>
                  {history.map((item, index) => (
                    <React.Fragment key={item.thread_id}>
                      <ListItem 
                        button 
                        onClick={() => { setThreadId(item.thread_id); setAuditData(null); setTabValue(0); }}
                        sx={{ borderRadius: 2, mb: 1, '&:hover': { bgcolor: 'primary.50' } }}
                      >
                        <ListItemText 
                          primary={item.filename} 
                          secondary={new Date(item.created_at).toLocaleString('es-ES', { dateStyle: 'medium', timeStyle: 'short' })} 
                        />
                        <ListItemSecondaryAction sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                          <Box sx={{ textAlign: 'right' }}>
                            <Typography variant="body2" fontWeight="black" color="primary.main">
                              {item.score}% Evidencias
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              Encontradas
                            </Typography>
                          </Box>
                          <Chip 
                            label={item.status === 'completed' ? 'Finalizado' : 'En proceso'} 
                            color={item.status === 'completed' ? 'success' : 'warning'} 
                            size="small" 
                            sx={{ fontWeight: 'bold' }}
                          />
                          <IconButton edge="end" color="primary" onClick={() => { setThreadId(item.thread_id); setAuditData(null); setTabValue(0); }}>
                            <VisibilityIcon />
                          </IconButton>
                        </ListItemSecondaryAction>
                      </ListItem>
                      {index < history.length - 1 && <Divider component="li" />}
                    </React.Fragment>
                  ))}
                </List>
              )}
            </Box>
          )}

          {/* ── PESTAÑA 2: Configurar Indicadores ── */}
          {tabValue === 2 && (
            <Box>
              <Typography variant="h6" gutterBottom fontWeight="bold">Matriz de Búsqueda Personalizada</Typography>
              <Typography variant="body2" color="text.secondary" mb={3}>
                Defina qué indicadores desea buscar. Cargue un Excel/CSV con las columnas: <strong>NEIS, Epígrafe e Indicador</strong>.
              </Typography>
              
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 4 }}>
                <Button variant="outlined" component="label" sx={{ height: 56, flexGrow: 1, borderRadius: 2, borderStyle: 'dashed', borderWidth: 2 }} startIcon={<CloudUploadIcon />}>
                  {indicatorsFile ? indicatorsFile.name : 'Cargar Nueva Matriz de Indicadores'}
                  <input type="file" hidden accept=".xlsx,.csv" onChange={(e) => setIndicatorsFile(e.target.files[0])} />
                </Button>
                <Button 
                  variant="contained" 
                  color="secondary"
                  onClick={handleUploadIndicators} 
                  disabled={uploadingIndicators || !indicatorsFile} 
                  sx={{ height: 56, px: 4, borderRadius: 2, fontWeight: 'bold' }}
                >
                  {uploadingIndicators ? <CircularProgress size={24} color="inherit" /> : 'Actualizar Matriz'}
                </Button>
              </Box>
              {error && <Typography color="error" sx={{ mt: 2, mb: 2 }}>{error}</Typography>}

              <Divider sx={{ mb: 3 }} />

              <Typography variant="h6" gutterBottom>Indicadores Activos ({indicators.length})</Typography>
              {loadingIndicators ? (
                 <CircularProgress size={24} />
              ) : (
                <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 400, borderRadius: 2 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell width={50}><strong>ID</strong></TableCell>
                        <TableCell width={150}><strong>Referencia</strong></TableCell>
                        <TableCell><strong>Indicador / Pregunta de Búsqueda</strong></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {indicators.map((ind) => (
                        <TableRow key={ind.id} hover>
                          <TableCell>{ind.id}</TableCell>
                          <TableCell><Typography variant="caption" sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}>{ind.ref}</Typography></TableCell>
                          <TableCell><Typography variant="body2">{ind.question}</Typography></TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          )}
        </Box>
      </Paper>

      {/* ── Tabla de hallazgos (Solo visible si hay Thread y estamos en Tab 0) ── */}
      {threadId && tabValue === 0 && (
        <Paper sx={{ p: 4, borderRadius: 3 }} elevation={4}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
            <Box>
              <Typography variant="h5" fontWeight="black" color="slate.900">
                Hallazgos y Evidencias
              </Typography>
              {auditData?.filename && <Typography variant="body2" color="text.secondary">Documento: {auditData.filename} ({completedCount} de {totalIndicators} indicadores analizados)</Typography>}
            </Box>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              {isProcessing && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, bgcolor: 'primary.50', px: 2, py: 1, borderRadius: 2 }}>
                  <CircularProgress size={20} />
                  <Typography color="primary.main" variant="body2" fontWeight="bold">Buscando evidencias...</Typography>
                </Box>
              )}
              {isCompleted && <Chip label="✓ Análisis Finalizado" color="success" sx={{ fontWeight: 'bold' }} />}
              {auditData?.status === 'error' && <Chip label="✗ Error en proceso" color="error" />}
              {isCompleted && (
                <Button
                  variant="outlined"
                  startIcon={<DownloadIcon />}
                  onClick={() => exportToCSV(results, indicatorsMap, exportFilename)}
                  sx={{ borderRadius: 2, fontWeight: 'bold' }}
                >
                  Descargar Reporte
                </Button>
              )}
            </Box>
          </Box>

          <TableContainer sx={{ maxHeight: 600, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell width={50}><strong>ID</strong></TableCell>
                  <TableCell width={130}><strong>Referencia</strong></TableCell>
                  <TableCell><strong>Indicador</strong></TableCell>
                  <TableCell width={140}><strong>Evidencia</strong></TableCell>
                  <TableCell width={70}><strong>Página</strong></TableCell>
                  <TableCell><strong>Cita Literal</strong></TableCell>
                  <TableCell><strong>Razonamiento AI</strong></TableCell>
                  <TableCell width={110}><strong>Validación</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {completedCount === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} align="center" sx={{ py: 10 }}>
                      {isProcessing ? (
                        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                          <CircularProgress />
                          <Typography color="text.secondary">El Analizador está extrayendo información del PDF...</Typography>
                        </Box>
                      ) : 'Sin hallazgos'}
                    </TableCell>
                  </TableRow>
                ) : (
                  Object.values(results)
                    .sort((a, b) => Number(a.indicator_id) - Number(b.indicator_id))
                    .map((row) => {
                      const ind = indicatorsMap[row.indicator_id] || {};
                      return (
                        <TableRow key={row.indicator_id} hover>
                          <TableCell><strong>{row.indicator_id}</strong></TableCell>
                          <TableCell>
                            <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary', fontWeight: 'bold' }}>
                              {ind.ref || '—'}
                            </Typography>
                          </TableCell>
                          <TableCell sx={{ maxWidth: 220, whiteSpace: 'normal', fontSize: '0.82rem' }}>
                            <Tooltip title={ind.question || ''} placement="top" arrow>
                              <span>{ind.question || '—'}</span>
                            </Tooltip>
                          </TableCell>
                          <TableCell><EvidenciaChip value={row.cumple} /></TableCell>
                          <TableCell align="center" sx={{ fontWeight: 'bold' }}>{row.pagina_real}</TableCell>
                          <TableCell sx={{ maxWidth: 260, whiteSpace: 'normal', fontSize: '0.8rem', color: 'text.secondary', fontStyle: row.evidencia_literal ? 'italic' : 'normal' }}>
                            {row.evidencia_literal || '—'}
                          </TableCell>
                          <TableCell sx={{ maxWidth: 280, whiteSpace: 'normal', fontSize: '0.8rem' }}>
                            {(() => {
                              const raz = row.razonamiento;
                              if (!raz) return '—';
                              if (typeof raz === 'string') return raz;
                              if (typeof raz === 'object') {
                                return (
                                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                                    {raz.comparativa_normativa && (
                                      <Typography variant="caption" display="block" sx={{ fontSize: '0.78rem' }}>
                                        <strong>Comparativa:</strong> {raz.comparativa_normativa}
                                      </Typography>
                                    )}
                                    {raz.ubicacion_contextual && (
                                      <Typography variant="caption" display="block" sx={{ fontSize: '0.78rem', color: 'text.secondary' }}>
                                        <strong>Ubicación:</strong> {raz.ubicacion_contextual}
                                      </Typography>
                                    )}
                                    {raz.justificacion_vacios && (
                                      <Typography variant="caption" display="block" sx={{ fontSize: '0.78rem', color: 'error.main' }}>
                                        <strong>Vacíos:</strong> {raz.justificacion_vacios}
                                      </Typography>
                                    )}
                                  </Box>
                                );
                              }
                              return String(raz);
                            })()}
                          </TableCell>
                          <TableCell>
                            <FormControlLabel
                              control={
                                <Switch
                                  size="small"
                                  checked={row.human_validation === true}
                                  onChange={() => handleFeedbackToggle(row.indicator_id, row.human_validation)}
                                  color="primary"
                                />
                              }
                              label={<Typography variant="caption" sx={{ fontWeight: 'bold' }}>{row.human_validation ? 'SÍ' : 'NO'}</Typography>}
                            />
                          </TableCell>
                        </TableRow>
                      );
                    })
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}
    </Box>
  );
}
