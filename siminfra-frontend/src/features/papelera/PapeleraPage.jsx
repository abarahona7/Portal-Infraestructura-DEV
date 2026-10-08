import { useCallback, useEffect, useState } from 'react';
import { Download, RotateCcw, Trash2, X } from 'lucide-react';
import apiClient from '../../api/client';
import './PapeleraPage.css';

const MODULE_NAMES = {
  usuarios: 'Usuarios', equipos: 'Equipos', 'perfiles-genericos': 'Perfiles genéricos',
  anexos: 'Anexos', ips: 'IPs', 'pcs-genericos': 'PCs genéricos',
  servidores: 'Servidores', departamentos: 'Departamentos', subareas: 'Áreas',
};

const formatDate = (value) => value ? new Date(value).toLocaleString('es-CL') : 'Sin fecha';
const labelFor = (field) => field.replaceAll('_', ' ').replace(/^./, (character) => character.toLocaleUpperCase('es-CL'));
const visibleFields = (record) => Object.entries(record || {}).filter(([key, value]) => (
  !['historial', 'equipos', 'archive_context', 'deleted_at', 'deleted_by'].includes(key)
  && !/password|contraseña|pin|secret/i.test(key)
  && (value === null || ['string', 'number', 'boolean'].includes(typeof value))
));

export default function PapeleraPage({ requestConfirmation, showToast }) {
  const [rows, setRows] = useState([]);
  const [module, setModule] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/papelera/', { params: { ...(module ? { modulo: module } : {}), page } });
      setRows(response.data.results);
      if (response.data.page !== page) setPage(response.data.page);
      setTotalPages(response.data.total_pages);
      setTotal(response.data.count);
    } catch {
      showToast?.('No se pudo cargar la Papelera.', 'error');
    } finally {
      setLoading(false);
    }
  }, [module, page, showToast]);

  useEffect(() => {
    let cancelled = false;
    apiClient.get('/papelera/', { params: { ...(module ? { modulo: module } : {}), page } })
      .then(({ data }) => {
        if (!cancelled) {
          setRows(data.results);
          if (data.page !== page) setPage(data.page);
          setTotalPages(data.total_pages);
          setTotal(data.count);
        }
      })
      .catch(() => { if (!cancelled) showToast?.('No se pudo cargar la Papelera.', 'error'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [module, page, showToast]);

  const openDetail = async (row) => {
    try {
      const response = await apiClient.get(`/papelera/${row.modulo}/${row.id}/`);
      setSelected({ ...row, ...response.data });
    } catch {
      showToast?.('No se pudo cargar el registro archivado.', 'error');
    }
  };

  const restore = async (row) => {
    const confirmed = await requestConfirmation?.({
      title: 'Restaurar registro',
      message: `¿Deseas restaurar "${row.nombre}"? Sus asignaciones anteriores no se recuperarán automáticamente.`,
      confirmText: 'Restaurar',
    });
    if (confirmed === false) return;
    try {
      await apiClient.post(`/papelera/${row.modulo}/${row.id}/restaurar/`);
      setSelected(null);
      showToast?.('Registro restaurado. Revisa sus asignaciones antes de usarlo.', 'success');
      await reload();
    } catch (error) {
      const detail = error.response?.data?.detail;
      showToast?.(typeof detail === 'string' ? detail : 'No se pudo restaurar el registro.', 'error');
    }
  };

  const downloadReport = async () => {
    setExporting(true);
    try {
      const response = await apiClient.get('/papelera/reporte/', {
        params: module ? { modulo: module } : {},
        responseType: 'blob',
      });
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `papelera_${module || 'general'}_${new Date().toLocaleDateString('sv-SE')}.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch {
      showToast?.('No se pudo descargar el reporte de Papelera.', 'error');
    } finally {
      setExporting(false);
    }
  };

  return (
    <section className="papelera-page">
      <header className="papelera-heading">
        <div><h2>Papelera</h2><p>Registros retirados del portal. Solo administradores pueden consultarlos y restaurarlos.</p></div>
        <button type="button" onClick={reload}>Actualizar</button>
      </header>
      <div className="papelera-toolbar">
        <div className="papelera-filter">
          <label htmlFor="papelera-module">Módulo</label>
          <select id="papelera-module" value={module} onChange={(event) => { setPage(1); setModule(event.target.value); setLoading(true); }}>
            <option value="">Todos</option>
            {Object.entries(MODULE_NAMES).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select>
        </div>
        <button type="button" className="papelera-report-button" disabled={exporting} onClick={downloadReport}>
          <Download size={16} /> {exporting ? 'Preparando reporte…' : 'Descargar reporte Excel'}
        </button>
      </div>
      <p className="papelera-report-note">Incluye todos los registros actualmente en Papelera del módulo seleccionado, no solo esta página.</p>
      {loading ? <p className="papelera-empty">Cargando registros…</p> : rows.length === 0 ? (
        <p className="papelera-empty">No hay registros en Papelera.</p>
      ) : (
        <div className="papelera-list">
          {rows.map((row) => (
            <article className="papelera-row" key={`${row.modulo}-${row.id}`}>
              <span className="papelera-icon"><Trash2 size={18} /></span>
              <div className="papelera-row-main">
                <strong>{row.nombre}</strong>
                <span>{MODULE_NAMES[row.modulo]} · ID {row.id} · {formatDate(row.eliminado_en)} · {row.eliminado_por || 'Autor no registrado'}</span>
              </div>
              <div className="papelera-row-actions">
                <button type="button" onClick={() => openDetail(row)}>Ver ficha</button>
                <button type="button" onClick={() => restore(row)}><RotateCcw size={15} /> Restaurar</button>
              </div>
            </article>
          ))}
        </div>
      )}
      {!loading && total > 0 && <nav className="papelera-pagination" aria-label="Páginas de Papelera">
        <span>{total} registros · Página {page} de {totalPages}</span>
        <button type="button" disabled={page <= 1} onClick={() => { setLoading(true); setPage((value) => value - 1); }}>Anterior</button>
        <button type="button" disabled={page >= totalPages} onClick={() => { setLoading(true); setPage((value) => value + 1); }}>Siguiente</button>
      </nav>}
      {selected && (
        <div className="papelera-overlay" role="presentation">
          <section className="papelera-detail" role="dialog" aria-modal="true" aria-label="Ficha archivada">
            <header><div><small>{MODULE_NAMES[selected.modulo]} · ID {selected.id}</small><h3>{selected.nombre}</h3></div>
              <button type="button" onClick={() => setSelected(null)} aria-label="Cerrar ficha"><X size={20} /></button></header>
            <p>Archivado el {formatDate(selected.eliminado_en)} por {selected.eliminado_por || 'autor no registrado'}.</p>
            <dl className="papelera-fields">{visibleFields(selected.registro).map(([key, value]) => (
              <div key={key}><dt>{labelFor(key)}</dt><dd>{value == null || value === '' ? 'Sin registrar' : String(value)}</dd></div>
            ))}</dl>
            <h4>Movimientos de Papelera</h4>
            {selected.eventos?.map((event, index) => <p className="papelera-event" key={index}>
              <strong>{event.accion}</strong> · {formatDate(event.fecha)} · {event.realizado_por || 'Autor no registrado'}<br />{event.detalle}
            </p>)}
            {selected.historial?.length > 0 && <>
              <h4>Historial del módulo</h4>
              <div className="papelera-history">{selected.historial.map((entry, index) => (
                <details key={entry.id || index}>
                  <summary>{entry.accion_nombre || entry.accion} · {formatDate(entry.fecha_movimiento)} · {entry.modificado_por || entry.realizado_por || 'Autor no registrado'}</summary>
                  <p>{entry.observacion || 'Movimiento registrado sin observación adicional.'}</p>
                </details>
              ))}</div>
            </>}
            <button type="button" className="papelera-restore" onClick={() => restore(selected)}><RotateCcw size={16} /> Restaurar registro</button>
          </section>
        </div>
      )}
    </section>
  );
}
