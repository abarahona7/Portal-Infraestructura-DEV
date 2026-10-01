import { useEffect, useState } from 'react';
import apiClient from '../../../api/client';
import { downloadActa, downloadActaFirmada, downloadReporteActas, movimientoError } from '../../../api/movimientosApi';
import ActaGestionModal from '../../movimientos/components/ActaGestionModal';

const movementTypes = [
  ['ALTA', 'Alta'], ['ASIGNACION', 'Asignación'], ['REASIGNACION', 'Reasignación'],
  ['DEVOLUCION', 'Devolución'], ['CAMBIO', 'Cambio de equipo'], ['PRESTAMO', 'Préstamo'],
  ['INGRESO_REPARACION', 'Ingreso a reparación'], ['SALIDA_REPARACION', 'Salida de reparación'],
  ['BAJA', 'Baja'],
];
const actaStates = [
  ['BORRADOR', 'Borrador'], ['GENERADA', 'Generada'], ['PENDIENTE_FIRMA', 'Pendiente de firma'],
  ['FIRMADA', 'Firmada'], ['CERRADA', 'Cerrada'], ['ANULADA', 'Anulada'],
];
const emptyFilters = { folio: '', estado: '', tipo_movimiento: '', desde: '', hasta: '' };
const optionLabel = (options, value) => options.find(([key]) => key === value)?.[1] || value;

export default function ActaArchivoPanel({ role, onUpdated }) {
  const [filters, setFilters] = useState(emptyFilters);
  const [query, setQuery] = useState({});
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const [gestionActa, setGestionActa] = useState(null);
  const hasFilters = Object.values(filters).some(Boolean) || Object.keys(query).length > 0;

  useEffect(() => {
    const controller = new AbortController();
    apiClient.get('/actas/', { params: { ...query, page, page_size: 10 }, signal: controller.signal })
      .then(({ data: result }) => { setData(result); setError(''); setLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setError(movimientoError(err)); setLoading(false); } });
    return () => controller.abort();
  }, [query, page, revision]);

  const changeFilter = (field, value) => {
    setFilters((current) => ({ ...current, [field]: value }));
    setError('');
  };

  const search = (event) => {
    event.preventDefault();
    const folio = filters.folio.trim().toUpperCase();
    if (folio && !/^ATI-[0-9]{4}-[0-9]{6}$/.test(folio)) {
      setError('Escribe el folio completo con formato ATI-AAAA-######.');
      return;
    }
    if (filters.desde && filters.hasta && filters.desde > filters.hasta) {
      setError('La fecha final debe ser igual o posterior a la inicial.');
      return;
    }
    setData(null);
    setError('');
    setLoading(true);
    setPage(1);
    setQuery(Object.fromEntries(Object.entries({ ...filters, folio }).filter(([, value]) => value)));
  };

  const clearFilters = () => {
    setFilters(emptyFilters);
    setQuery({});
    setData(null);
    setError('');
    setLoading(true);
    setPage(1);
  };

  const exportReport = async () => {
    setExporting(true);
    setError('');
    try { await downloadReporteActas(query); }
    catch (err) { setError(movimientoError(err)); }
    finally { setExporting(false); }
  };
  const changePage = (nextPage) => { setData(null); setLoading(true); setPage(nextPage); };

  return <><section className="itam-dashboard-panel">
    <h3>Actas</h3>
    <p className="itam-dashboard-empty">Se crean automáticamente al registrar un movimiento. Aquí puedes buscarlas, descargarlas y revisar su firma.</p>
    <form className="itam-dashboard-report-form" onSubmit={search}>
      <label>Buscar por folio<input type="text" value={filters.folio} maxLength={15} placeholder="ATI-2026-000001" onChange={(event) => changeFilter('folio', event.target.value.toUpperCase())} /></label>
      <label>Estado<select value={filters.estado} onChange={(event) => changeFilter('estado', event.target.value)}>
        <option value="">Todos</option>{actaStates.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select></label>
      <button type="submit" disabled={loading}>{loading ? 'Buscando...' : 'Buscar'}</button>
      {hasFilters && <button type="button" className="itam-dashboard-clear-filters" onClick={clearFilters}>Mostrar todas</button>}
      <details className="itam-dashboard-filter-details">
        <summary>Más filtros</summary>
        <div className="itam-dashboard-report-form">
          <label>Tipo de movimiento<select value={filters.tipo_movimiento} onChange={(event) => changeFilter('tipo_movimiento', event.target.value)}>
            <option value="">Todos</option>{movementTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></label>
          <label>Emitida desde<input type="date" value={filters.desde} onChange={(event) => changeFilter('desde', event.target.value)} /></label>
          <label>Emitida hasta<input type="date" value={filters.hasta} onChange={(event) => changeFilter('hasta', event.target.value)} /></label>
        </div>
      </details>
    </form>
    {loading && <p role="status">Cargando actas...</p>}
    {error && <p className="itam-dashboard-error" role="alert">{error}</p>}
    {data && <>
      <p className="itam-dashboard-empty">{data.count ? `${data.count.toLocaleString('es-CL')} actas encontradas.` : 'No hay actas con esos filtros.'}</p>
      <div className="itam-dashboard-recent">
        {data.results.map((acta) => <article key={acta.id}>
          <div><strong>{acta.folio}</strong><span>{optionLabel(movementTypes, acta.tipo_movimiento)} · {optionLabel(actaStates, acta.estado)}</span></div>
          <time>{new Date(acta.fecha_emision).toLocaleString('es-CL')}</time>
          <div className="itam-dashboard-actions">
            <button type="button" onClick={() => downloadActa(acta).catch((err) => setError(movimientoError(err)))}>Descargar PDF</button>
            {acta.tiene_copia_firmada && <button type="button" onClick={() => downloadActaFirmada(acta).catch((err) => setError(movimientoError(err)))}>Copia firmada</button>}
            <button type="button" onClick={() => setGestionActa(acta)}>Estado y firma</button>
          </div>
        </article>)}
      </div>
      {data.total_pages > 1 && <div className="itam-dashboard-pager">
        <button type="button" disabled={loading || page <= 1} onClick={() => changePage(page - 1)}>Anterior</button>
        <span>Página {data.page} de {data.total_pages}</span>
        <button type="button" disabled={loading || page >= data.total_pages} onClick={() => changePage(page + 1)}>Siguiente</button>
      </div>}
      <button type="button" className="itam-dashboard-export-link" disabled={exporting || !data.count} onClick={exportReport}>{exporting ? 'Preparando planilla...' : 'Descargar listado para Excel (CSV)'}</button>
    </>}
  </section>{gestionActa && <ActaGestionModal initialActa={gestionActa} role={role} onClose={() => setGestionActa(null)} onUpdated={() => { setData(null); setLoading(true); setPage(1); setRevision((value) => value + 1); onUpdated?.(); }} />}</>;
}
