import { useCallback, useEffect, useState } from 'react';
import { ChevronDown, Download, RotateCcw, Trash2, X } from 'lucide-react';
import apiClient from '../../api/client';
import './PapeleraPage.css';

const MODULE_NAMES = {
  usuarios: 'Usuarios', equipos: 'Equipos', 'perfiles-genericos': 'Perfiles genéricos',
  anexos: 'Anexos', ips: 'IPs', 'pcs-genericos': 'PCs genéricos',
  servidores: 'Servidores', departamentos: 'Departamentos', subareas: 'Áreas',
};

const formatDate = (value) => value ? new Date(value).toLocaleString('es-CL') : 'Sin fecha';
const labelFor = (field) => field.replaceAll('_', ' ').replace(/^./, (character) => character.toLocaleUpperCase('es-CL'));
const PRIMARY_FIELDS = {
  usuarios: [
    ['Usuario de red', 'usuario_red'], ['Correo corporativo', 'correo_corp'],
    ['Departamento', 'departamento_nombre', 'dpto_area'], ['Área', 'subarea_nombre'],
    ['Cargo', 'cargo'], ['Estado al archivar', 'estado'],
  ],
  equipos: [
    ['Tipo', 'tipo'], ['Marca', 'marca'], ['Modelo', 'modelo'],
    ['N.º de serie', 'numero_serie'], ['Activo fijo', 'activo_fijo', 'af'],
    ['Estado al archivar', 'estado'], ['Asignado a', 'usuario_nombre'],
    ['Departamento', 'departamento_nombre'],
  ],
  'perfiles-genericos': [
    ['Tipo', 'tipo'], ['Usuario', 'usuario'], ['Correo', 'correo'],
    ['Departamento', 'departamento_nombre', 'dpto_area'], ['Estado al archivar', 'estado'],
  ],
  anexos: [['Número', 'numero_anexo'], ['Usuario', 'usuario_nombre'], ['Estado al archivar', 'estado']],
  ips: [['Dirección IP', 'direccion_ip'], ['Estado al archivar', 'estado']],
  'pcs-genericos': [
    ['Usuario local', 'usuario_local'], ['Hostname', 'hostname'],
    ['Departamento', 'departamento_nombre', 'dpto_area'],
    ['N.º de serie', 'numero_serie'], ['Activo fijo', 'activo_fijo'],
  ],
  servidores: [['Hostname', 'hostname'], ['Dirección IP', 'ip'], ['Descripción', 'descripcion']],
  departamentos: [['Nombre', 'nombre'], ['Activo', 'activo']],
  subareas: [['Nombre', 'nombre'], ['Departamento', 'departamento_nombre'], ['Activo', 'activo']],
};
const HIDDEN_FIELDS = new Set([
  'id', 'historial', 'equipos', 'archive_context', 'deleted_at', 'deleted_by',
  'departamento', 'subarea', 'usuario', 'fecha_creacion', 'fecha_actualizacion',
  'protocolos_estado', 'anexo_actual', 'nombre_completo', 'nombre',
]);
const hasValue = (value) => value !== null && value !== undefined && value !== '';
const displayValue = (value) => typeof value === 'boolean' ? (value ? 'Sí' : 'No') : String(value);

function recordFields(module, record) {
  const used = new Set();
  const primary = (PRIMARY_FIELDS[module] || []).flatMap(([label, ...keys]) => {
    keys.forEach((key) => used.add(key));
    const value = keys.map((key) => record?.[key]).find(hasValue);
    return hasValue(value) ? [{ label, value: displayValue(value) }] : [];
  });
  const additional = Object.entries(record || {}).filter(([key, value]) => (
    !used.has(key) && !HIDDEN_FIELDS.has(key)
    && !/password|contraseña|pin|secret|token|normalizado|_configured$|_id$|_nombre$/i.test(key)
    && hasValue(value) && value !== false
    && ['string', 'number', 'boolean'].includes(typeof value)
  )).map(([key, value]) => ({ label: labelFor(key), value: displayValue(value) }));
  return { primary, additional };
}

function FieldGrid({ fields }) {
  return <dl className="papelera-fields">{fields.map(({ label, value }) => (
    <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
  ))}</dl>;
}

export default function PapeleraPage({ requestConfirmation, showToast }) {
  const [rows, setRows] = useState([]);
  const [module, setModule] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!selected) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previousOverflow; };
  }, [selected]);

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

  const selectedFields = selected ? recordFields(selected.modulo, selected.registro) : null;

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
            <header className="papelera-detail-header"><div><span className="papelera-module-tag">{MODULE_NAMES[selected.modulo]}</span><h3>{selected.nombre}</h3>
              <p>Archivado el {formatDate(selected.eliminado_en)} · {selected.eliminado_por || 'Autor no registrado'}</p></div>
              <button type="button" onClick={() => setSelected(null)} aria-label="Cerrar ficha"><X size={20} /></button></header>
            <div className="papelera-detail-body">
              <section className="papelera-primary"><h4>Datos principales</h4>
                {selectedFields.primary.length > 0
                  ? <FieldGrid fields={selectedFields.primary} />
                  : <p className="papelera-muted">No hay datos adicionales para mostrar.</p>}
              </section>
              {selectedFields.additional.length > 0 && <details className="papelera-detail-group">
                <summary><span>Otros datos <small>{selectedFields.additional.length}</small></span><ChevronDown size={16} /></summary>
                <FieldGrid fields={selectedFields.additional} />
              </details>}
              {(selected.eventos?.length > 0) && <details className="papelera-detail-group">
                <summary><span>Movimientos en Papelera <small>{selected.eventos.length}</small></span><ChevronDown size={16} /></summary>
                <div className="papelera-history">{selected.eventos.map((event, index) => <div className="papelera-event" key={index}>
                  <strong>{event.accion}</strong><span>{formatDate(event.fecha)} · {event.realizado_por || 'Autor no registrado'}</span>
                  {event.detalle && <p>{event.detalle}</p>}
                </div>)}</div>
              </details>}
              {(selected.historial?.length > 0) && <details className="papelera-detail-group">
                <summary><span>Historial del módulo <small>{selected.historial.length}</small></span><ChevronDown size={16} /></summary>
                <div className="papelera-history">{selected.historial.map((entry, index) => (
                  <details key={entry.id || index}>
                    <summary>{entry.accion_nombre || entry.accion} · {formatDate(entry.fecha_movimiento)}</summary>
                    <p>{entry.modificado_por || entry.realizado_por || 'Autor no registrado'} · {entry.observacion || 'Movimiento registrado sin observación adicional.'}</p>
                  </details>
                ))}</div>
              </details>}
            </div>
            <footer className="papelera-detail-footer"><span>Registro #{selected.id} · En Papelera</span>
              <button type="button" className="papelera-restore" onClick={() => restore(selected)}><RotateCcw size={16} /> Restaurar registro</button></footer>
          </section>
        </div>
      )}
    </section>
  );
}
