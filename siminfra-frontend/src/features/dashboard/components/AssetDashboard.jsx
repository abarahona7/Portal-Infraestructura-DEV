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

export default function AssetDashboard({ onOpenHistory }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    apiClient.get('/activos/resumen/', { signal: controller.signal })
      .then(({ data: response }) => { setData(response); setError(''); setLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setError(movimientoError(err)); setLoading(false); } });
    return () => controller.abort();
  }, [reloadKey]);

  return <div className="itam-dashboard">
    <div className="itam-dashboard-heading">
      <div><span className="itam-dashboard-eyebrow">Inventario TI</span><h2>Resumen de activos</h2><p>Estado actual del maestro de equipos y movimientos registrados en el nuevo módulo.</p></div>
      <button type="button" className="itam-dashboard-refresh" disabled={loading} onClick={() => { setLoading(true); setReloadKey((value) => value + 1); }}><RefreshCw size={17} />Actualizar</button>
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
        <p>Los activos sin custodio incluyen equipos disponibles, en reparación y dados de baja: {data.conteos.sin_custodio.toLocaleString('es-CL')}.</p>
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
