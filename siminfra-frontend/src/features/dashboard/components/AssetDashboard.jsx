import { useEffect, useState } from 'react';
import { Download, RefreshCw } from 'lucide-react';
import apiClient from '../../../api/client';
import { downloadActa, movimientoError } from '../../../api/movimientosApi';
import './AssetDashboard.css';

const cards = [
  ['total', 'Total de activos'],
  ['disponibles', 'Disponibles'],
  ['asignados', 'Asignados'],
  ['en_reparacion', 'En reparación'],
  ['en_prestamo', 'En préstamo'],
  ['dados_de_baja', 'Dados de baja'],
];

function Distribution({ title, items, empty }) {
  const max = Math.max(...items.map((item) => item.total), 1);
  return <section className="itam-dashboard-panel">
    <h3>{title}</h3>
    {!items.length && <p className="itam-dashboard-empty">{empty}</p>}
    <div className="itam-dashboard-bars">
      {items.map((item) => <div className="itam-dashboard-bar-row" key={item.nombre}>
        <span className="itam-dashboard-bar-label" title={item.nombre}>{item.nombre}</span>
        <div className="itam-dashboard-track" aria-hidden="true"><span style={{ width: `${item.total / max * 100}%` }} /></div>
        <strong>{item.total.toLocaleString('es-CL')}</strong>
      </div>)}
    </div>
  </section>;
}

export default function AssetDashboard({ onOpenHistory, onEditAsset }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const [showAllPending, setShowAllPending] = useState(false);
  const [pendingPage, setPendingPage] = useState(1);
  const [pendingData, setPendingData] = useState(null);
  const [pendingLoading, setPendingLoading] = useState(false);
  const [pendingError, setPendingError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    apiClient.get('/activos/resumen/', { signal: controller.signal })
      .then(({ data: response }) => { setData(response); setError(''); setLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setError(movimientoError(err)); setLoading(false); } });
    return () => controller.abort();
  }, [reloadKey]);

  useEffect(() => {
    if (!showAllPending) return undefined;
    const controller = new AbortController();
    apiClient.get('/activos/pendientes-tecnicos/', {
      params: { page: pendingPage, page_size: 20 }, signal: controller.signal,
    }).then(({ data: response }) => { setPendingData(response); setPendingError(''); setPendingLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setPendingError(movimientoError(err)); setPendingLoading(false); } });
    return () => controller.abort();
  }, [showAllPending, pendingPage, reloadKey]);

  const changePendingPage = (nextPage) => { setPendingData(null); setPendingLoading(true); setPendingPage(nextPage); };
  const pendingRows = showAllPending ? (pendingData?.results || []) : (data?.pendientes_tecnicos || []);

  return <div className="itam-dashboard">
    <div className="itam-dashboard-heading">
      <div><span className="itam-dashboard-eyebrow">Inventario TI</span><h2>Resumen de activos</h2><p>Estado actual del maestro de equipos y movimientos registrados en el nuevo módulo.</p></div>
      <button type="button" className="itam-dashboard-refresh" disabled={loading} onClick={() => { setLoading(true); if (showAllPending) { setPendingPage(1); setPendingData(null); setPendingLoading(true); } setReloadKey((value) => value + 1); }}><RefreshCw size={17} />Actualizar</button>
    </div>
    {loading && !data && <p role="status">Cargando indicadores...</p>}
    {error && <p className="itam-dashboard-error" role="alert">{error}</p>}
    {data && <>
      <div className="itam-dashboard-cards">
        {cards.map(([key, label]) => <div className="itam-dashboard-card" key={key}><span>{label}</span><strong>{data.conteos[key].toLocaleString('es-CL')}</strong></div>)}
      </div>
      <div className="itam-dashboard-context">
        <span><strong>{data.movimientos_30_dias.toLocaleString('es-CL')}</strong> movimientos en los últimos 30 días</span>
        <span>Actualizado: {new Date(data.actualizado_en).toLocaleString('es-CL')}</span>
      </div>
      <section className="itam-dashboard-panel itam-dashboard-review">
        <h3>Datos que requieren revisión</h3>
        <div><span>Sin número de serie</span><strong>{data.conteos.sin_serie.toLocaleString('es-CL')}</strong></div>
        <div><span>Sin activo fijo</span><strong>{data.conteos.sin_activo_fijo.toLocaleString('es-CL')}</strong></div>
        <div><span>Asignados a colaboradores no activos</span><strong>{data.conteos.con_custodio_inactivo.toLocaleString('es-CL')}</strong></div>
        <div><span>Celulares sin IMEI</span><strong>{data.conteos.sin_imei_celular.toLocaleString('es-CL')}</strong></div>
        <div><span>Notebook o Mac sin Hostname</span><strong>{data.conteos.sin_hostname_computador.toLocaleString('es-CL')}</strong></div>
        <div><span>Notebook o Mac sin MAC</span><strong>{data.conteos.sin_mac_computador.toLocaleString('es-CL')}</strong></div>
        <p><strong>{data.conteos.fichas_tecnicas_incompletas.toLocaleString('es-CL')}</strong> fichas técnicas incompletas en total, sin contar dos veces un equipo al que le falten varios datos. Se excluyen los dados de baja.</p>
        <p>Los activos sin custodio incluyen equipos disponibles, en reparación y dados de baja: {data.conteos.sin_custodio.toLocaleString('es-CL')}.</p>
      </section>
      <section className="itam-dashboard-panel">
        <h3>Fichas técnicas por completar</h3>
        {!data.conteos.fichas_tecnicas_incompletas && <p className="itam-dashboard-empty">No hay fichas técnicas pendientes en activos vigentes.</p>}
        {(data.conteos.fichas_tecnicas_incompletas > 0 || showAllPending) && <div className="itam-dashboard-pending-heading">
          <p className="itam-dashboard-empty">{showAllPending ? 'Todos los pendientes, ordenados por registro más reciente.' : 'Diez registros recientes; el total incluye todos los pendientes.'}</p>
          <button type="button" onClick={() => {
            if (showAllPending) { setShowAllPending(false); setPendingData(null); }
            else { setPendingPage(1); setPendingLoading(true); setShowAllPending(true); }
          }}>{showAllPending ? 'Mostrar recientes' : `Ver todos (${data.conteos.fichas_tecnicas_incompletas})`}</button>
        </div>}
        {showAllPending && pendingLoading && <p role="status">Cargando fichas pendientes...</p>}
        {showAllPending && pendingError && <p className="itam-dashboard-error" role="alert">{pendingError}</p>}
        <div className="itam-dashboard-recent">
          {pendingRows.map((item) => <article key={item.id}>
            <div><strong>{item.tipo} {item.marca} {item.modelo}</strong><span>Serie: {item.numero_serie || 'N/I'} · AF: {item.af || 'N/I'} · ID: {item.id}</span><span>Falta: {item.faltantes.join(', ')}</span></div>
            <span>{item.estado}</span>
            <div className="itam-dashboard-actions"><button type="button" onClick={() => onEditAsset(item)}>Editar ficha</button></div>
          </article>)}
        </div>
        {showAllPending && pendingData && pendingData.total_pages > 1 && <div className="itam-dashboard-pager">
          <button type="button" disabled={pendingLoading || pendingPage <= 1} onClick={() => changePendingPage(pendingPage - 1)}>Anterior</button>
          <span>Página {pendingData.page} de {pendingData.total_pages}</span>
          <button type="button" disabled={pendingLoading || pendingPage >= pendingData.total_pages} onClick={() => changePendingPage(pendingPage + 1)}>Siguiente</button>
        </div>}
      </section>
      <div className="itam-dashboard-distributions">
        <Distribution title="Por tipo" items={data.por_tipo} empty="Todavía no hay activos." />
        <Distribution title="Por ubicación" items={data.por_ubicacion} empty="Todavía no hay ubicaciones." />
        <Distribution title="Por área asignada" items={data.por_area} empty="Todavía no hay activos asignados." />
      </div>
      <section className="itam-dashboard-panel">
        <h3>Últimos movimientos</h3>
        {!data.ultimos_movimientos.length && <p className="itam-dashboard-empty">Aún no hay movimientos en la nueva trazabilidad.</p>}
        <div className="itam-dashboard-recent">
          {data.ultimos_movimientos.map((item) => <article key={item.id}>
            <div><strong>{item.tipo_movimiento}</strong><span>{item.activo} · {item.folio || 'Sin acta'}</span></div>
            <time>{new Date(item.fecha_movimiento).toLocaleString('es-CL')}</time>
            <div className="itam-dashboard-actions">
              <button type="button" onClick={() => onOpenHistory({ id: item.activo_id, tipo: item.activo })}>Historial</button>
              {item.acta_id && <button type="button" title={`Descargar acta ${item.folio}`} onClick={() => downloadActa({ id: item.acta_id, folio: item.folio }).catch((err) => setError(movimientoError(err)))}><Download size={15} /> Acta</button>}
            </div>
          </article>)}
        </div>
      </section>
    </>}
  </div>;
}
