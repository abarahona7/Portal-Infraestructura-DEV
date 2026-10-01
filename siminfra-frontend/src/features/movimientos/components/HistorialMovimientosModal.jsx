import { useEffect, useState } from 'react';
import { downloadActa, downloadActaFirmada, getMovimientos, movimientoError } from '../../../api/movimientosApi';
import MovimientoShell from './MovimientoShell';
import CambioResumen from './CambioResumen';

export default function HistorialMovimientosModal({ activo, onClose }) {
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ results: [], count: 0, total_pages: 1 });
  const [error, setError] = useState('');
  const [operacionId, setOperacionId] = useState(null);
  useEffect(() => {
    if (!activo) return undefined;
    const controller = new AbortController();
    getMovimientos({ activo_id: activo.id, page, page_size: 20 }, controller.signal)
      .then(setData).catch((err) => { if (err.code !== 'ERR_CANCELED') setError(movimientoError(err)); })
    return () => controller.abort();
  }, [activo, page]);
  if (!activo) return null;
  return <MovimientoShell title={`Movimientos · ${activo.tipo} ${activo.marca || ''} ${activo.modelo || ''}`} onClose={onClose} footer={<button type="button" className="movimiento-button" onClick={onClose}>Cerrar</button>}>
    <p className="movimiento-note">Serie: {activo.numero_serie || 'N/I'} · Activo fijo: {activo.af || 'N/I'} · Estado actual: {activo.estado}</p>
    {error && <p role="alert" className="movimiento-error">{error}</p>}
    {operacionId && <CambioResumen key={operacionId} operacionId={operacionId} onClose={() => setOperacionId(null)} />}
    {!data.count && <p>Este activo todavía no tiene movimientos registrados en el nuevo módulo.</p>}
    {data.results.map((item) => <article key={item.id} className="movimiento-entry">
      <div className="movimiento-entry-header"><h4>{item.tipo_movimiento}</h4><time>{new Date(item.fecha_movimiento).toLocaleString('es-CL')}</time></div>
      <dl className="movimiento-summary"><dt>Colaborador</dt><dd>{(item.colaborador_destino || item.colaborador_origen)?.nombre_completo || 'Inventario TI'}</dd><dt>Área</dt><dd>{(item.colaborador_destino || item.colaborador_origen)?.area || '—'}</dd><dt>Ubicación</dt><dd>{item.ubicacion_destino}</dd><dt>Estado</dt><dd>{item.estado_operativo_resultante} · {item.estado_fisico}</dd><dt>Usuario TI</dt><dd>{item.ejecutado_por}</dd><dt>Folio</dt><dd>{item.acta?.folio || '—'}</dd></dl>
      {item.operacion_id && <button className="movimiento-button" type="button" onClick={() => setOperacionId(item.operacion_id)}>Ver cambio de equipo completo</button>}
      {item.acta && <>
        <button className="movimiento-button" type="button" onClick={() => downloadActa(item.acta).catch((err) => setError(movimientoError(err)))}>Descargar comprobante</button>
        {item.acta.tiene_copia_firmada && <button className="movimiento-button" type="button" onClick={() => downloadActaFirmada(item.acta).catch((err) => setError(movimientoError(err)))}>Descargar copia firmada</button>}
      </>}
    </article>)}
    {data.total_pages > 1 && <div className="movimiento-pager"><button className="movimiento-button" disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</button><span>Página {page} de {data.total_pages}</span><button className="movimiento-button" disabled={page >= data.total_pages} onClick={() => setPage(page + 1)}>Siguiente</button></div>}
  </MovimientoShell>;
}
