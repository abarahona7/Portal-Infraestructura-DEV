import { useEffect, useState } from 'react';
import { downloadActa, getMovimientos, movimientoError } from '../../../api/movimientosApi';
import MovimientoShell from './MovimientoShell';
import CambioResumen from './CambioResumen';
import ActaGestionModal from './ActaGestionModal';

const assetLabel = (asset) => [asset.tipo, asset.marca, asset.modelo].filter(Boolean).join(' ') || `Activo #${asset.id}`;

export default function HistorialColaboradorModal({ colaborador, onClose, onOpenAsset, role }) {
  const [page, setPage] = useState(1);
  const [gestionActa, setGestionActa] = useState(null);
  const [revision, setRevision] = useState(0);
  const [data, setData] = useState({ results: [], count: 0, total_pages: 1 });
  const [error, setError] = useState('');
  const [operacionId, setOperacionId] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    getMovimientos({ colaborador_id: colaborador.id, page, page_size: 20 }, controller.signal)
      .then((result) => { setData(result); setLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setError(movimientoError(err)); setLoading(false); } });
    return () => controller.abort();
  }, [colaborador.id, page, revision]);

  const current = colaborador.equipos || [];
  return <>{!gestionActa && <MovimientoShell title={`Activos de ${colaborador.nombre_completo}`} onClose={onClose} footer={<button type="button" className="movimiento-button" onClick={onClose}>Cerrar</button>}>
    <h4>Activos actualmente asignados</h4>
    {!current.length && <p className="movimiento-note">Este colaborador no tiene equipos asignados actualmente.</p>}
    {current.map((asset) => <article className="movimiento-entry" key={asset.id}>
      <div className="movimiento-entry-header"><strong>{assetLabel(asset)}</strong><span>{asset.estado}</span></div>
      <span>Serie: {asset.numero_serie || 'N/I'} · Activo fijo: {asset.af || 'N/I'} · Desde: {asset.fecha_asignacion || 'Fecha no registrada'}</span>
      <button type="button" className="movimiento-button" onClick={() => { onOpenAsset(asset); onClose(); }}>Ver historial del activo</button>
    </article>)}
    <h4>Movimientos del colaborador</h4>
    <p className="movimiento-note">Los movimientos anteriores a la puesta en marcha de la nueva trazabilidad permanecen en el historial legado del portal.</p>
    {loading && <p>Cargando movimientos...</p>}
    {error && <p className="movimiento-error" role="alert">{error}</p>}
    {operacionId && <CambioResumen key={operacionId} operacionId={operacionId} onClose={() => setOperacionId(null)} />}
    {!loading && !error && !data.count && <p>No hay movimientos en la nueva trazabilidad.</p>}
    {data.results.map((item) => {
      const asset = item.snapshot?.despues || { id: item.activo_id };
      return <article className="movimiento-entry" key={item.id}>
        <div className="movimiento-entry-header"><strong>{item.tipo_movimiento} · {assetLabel(asset)}</strong><time>{new Date(item.fecha_movimiento).toLocaleString('es-CL')}</time></div>
        <span>Serie: {asset.numero_serie || 'N/I'} · Ubicación: {item.ubicacion_destino} · Estado: {item.estado_operativo_resultante}</span>
        <span>Folio: {item.acta?.folio || '—'} · Registrado por: {item.ejecutado_por}</span>
        {item.operacion_id && <button type="button" className="movimiento-button" onClick={() => setOperacionId(item.operacion_id)}>Ver cambio de equipo completo</button>}
        {item.acta && <button type="button" className="movimiento-button" onClick={() => downloadActa(item.acta).catch((err) => setError(movimientoError(err)))}>Descargar acta {item.acta.folio}</button>}
      </article>;
    })}
    {data.total_pages > 1 && <div className="movimiento-pager"><button type="button" className="movimiento-button" disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</button><span>Página {page} de {data.total_pages}</span><button type="button" className="movimiento-button" disabled={page >= data.total_pages} onClick={() => setPage(page + 1)}>Siguiente</button></div>}
  </MovimientoShell>}{gestionActa && <ActaGestionModal initialActa={gestionActa} role={role} onClose={() => setGestionActa(null)} onUpdated={() => setRevision((value) => value + 1)} />}</>;
}
