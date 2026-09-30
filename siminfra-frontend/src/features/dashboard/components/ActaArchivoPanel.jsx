import { useEffect, useState } from 'react';
import apiClient from '../../../api/client';
import { downloadActa, downloadActaFirmada, movimientoError } from '../../../api/movimientosApi';
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

export default function ActaArchivoPanel({ role, onUpdated }) {
  const [filters, setFilters] = useState({ estado: '', tipo_movimiento: '' });
  const [query, setQuery] = useState(null);
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [gestionActa, setGestionActa] = useState(null);

  useEffect(() => {
    if (!query) return undefined;
    const controller = new AbortController();
    apiClient.get('/actas/', { params: { ...query, page, page_size: 20 }, signal: controller.signal })
      .then(({ data: result }) => { setData(result); setError(''); setLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setError(movimientoError(err)); setLoading(false); } });
    return () => controller.abort();
  }, [query, page, revision]);

  const changeFilter = (field, value) => {
    setFilters((current) => ({ ...current, [field]: value }));
    setQuery(null);
    setData(null);
    setError('');
    setLoading(false);
  };

  const search = (event) => {
    event.preventDefault();
    setData(null);
    setError('');
    setLoading(true);
    setPage(1);
    setQuery({ ...filters });
  };
  const changePage = (nextPage) => { setData(null); setLoading(true); setPage(nextPage); };

  return <><section className="itam-dashboard-panel">
    <h3>Archivo de actas ITAM</h3>
    <p className="itam-dashboard-empty">Consulta actas de cualquier estado. La lista se carga al pulsar «Consultar».</p>
    <form className="itam-dashboard-report-form" onSubmit={search}>
      <label>Estado<select value={filters.estado} onChange={(event) => changeFilter('estado', event.target.value)}>
        <option value="">Todos</option>{actaStates.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select></label>
      <label>Tipo de movimiento<select value={filters.tipo_movimiento} onChange={(event) => changeFilter('tipo_movimiento', event.target.value)}>
        <option value="">Todos</option>{movementTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select></label>
      <button type="submit" disabled={loading}>{loading ? 'Consultando...' : 'Consultar'}</button>
    </form>
    {loading && <p role="status">Cargando actas...</p>}
    {error && <p className="itam-dashboard-error" role="alert">{error}</p>}
    {data && <>
      <p className="itam-dashboard-empty">{data.count.toLocaleString('es-CL')} actas encontradas.</p>
      <div className="itam-dashboard-recent">
        {data.results.map((acta) => <article key={acta.id}>
          <div><strong>{acta.folio}</strong><span>{acta.tipo_movimiento.replaceAll('_', ' ')} · {acta.estado.replaceAll('_', ' ')}</span></div>
          <time>{new Date(acta.fecha_emision).toLocaleString('es-CL')}</time>
          <div className="itam-dashboard-actions">
            <button type="button" onClick={() => downloadActa(acta).catch((err) => setError(movimientoError(err)))}>Original</button>
            {acta.tiene_copia_firmada && <button type="button" onClick={() => downloadActaFirmada(acta).catch((err) => setError(movimientoError(err)))}>Copia firmada</button>}
            <button type="button" onClick={() => setGestionActa(acta)}>Gestionar</button>
          </div>
        </article>)}
      </div>
      {data.total_pages > 1 && <div className="itam-dashboard-pager">
        <button type="button" disabled={loading || page <= 1} onClick={() => changePage(page - 1)}>Anterior</button>
        <span>Página {data.page} de {data.total_pages}</span>
        <button type="button" disabled={loading || page >= data.total_pages} onClick={() => changePage(page + 1)}>Siguiente</button>
      </div>}
    </>}
  </section>{gestionActa && <ActaGestionModal initialActa={gestionActa} role={role} onClose={() => setGestionActa(null)} onUpdated={() => { setData(null); setLoading(true); setPage(1); setRevision((value) => value + 1); onUpdated(); }} />}</>;
}
