import { useEffect, useState } from 'react';
import { Download, RefreshCw } from 'lucide-react';
import apiClient from '../../../api/client';
import { downloadActa, movimientoError } from '../../../api/movimientosApi';
import ActaGestionModal from '../../movimientos/components/ActaGestionModal';
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

export default function AssetDashboard({ onOpenHistory, onEditAsset, role }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const [showAllPending, setShowAllPending] = useState(false);
  const [pendingPage, setPendingPage] = useState(1);
  const [pendingData, setPendingData] = useState(null);
  const [pendingLoading, setPendingLoading] = useState(false);
  const [pendingError, setPendingError] = useState('');
  const [showAllActas, setShowAllActas] = useState(false);
  const [actaPage, setActaPage] = useState(1);
  const [actaData, setActaData] = useState(null);
  const [actaLoading, setActaLoading] = useState(false);
  const [actaError, setActaError] = useState('');
  const [gestionActa, setGestionActa] = useState(null);
  const [showAllCustody, setShowAllCustody] = useState(false);
  const [custodyPage, setCustodyPage] = useState(1);
  const [custodyData, setCustodyData] = useState(null);
  const [custodyLoading, setCustodyLoading] = useState(false);
  const [custodyError, setCustodyError] = useState('');

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

  useEffect(() => {
    if (!showAllActas) return undefined;
    const controller = new AbortController();
    apiClient.get('/actas/pendientes/', {
      params: { page: actaPage, page_size: 20 }, signal: controller.signal,
    }).then(({ data: response }) => { setActaData(response); setActaError(''); setActaLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setActaError(movimientoError(err)); setActaLoading(false); } });
    return () => controller.abort();
  }, [showAllActas, actaPage, reloadKey]);

  useEffect(() => {
    if (!showAllCustody) return undefined;
    const controller = new AbortController();
    apiClient.get('/activos/custodios-no-activos/', {
      params: { page: custodyPage, page_size: 20 }, signal: controller.signal,
    }).then(({ data: response }) => { setCustodyData(response); setCustodyError(''); setCustodyLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setCustodyError(movimientoError(err)); setCustodyLoading(false); } });
    return () => controller.abort();
  }, [showAllCustody, custodyPage, reloadKey]);

  const refreshDashboard = () => {
    setLoading(true);
    if (showAllPending) { setPendingPage(1); setPendingData(null); setPendingLoading(true); }
    if (showAllActas) { setActaPage(1); setActaData(null); setActaLoading(true); }
    if (showAllCustody) { setCustodyPage(1); setCustodyData(null); setCustodyLoading(true); }
    setReloadKey((value) => value + 1);
  };
  const changeActaPage = (nextPage) => { setActaData(null); setActaLoading(true); setActaPage(nextPage); };
  const changeCustodyPage = (nextPage) => { setCustodyData(null); setCustodyLoading(true); setCustodyPage(nextPage); };
  const changePendingPage = (nextPage) => { setPendingData(null); setPendingLoading(true); setPendingPage(nextPage); };
  const pendingRows = showAllPending ? (pendingData?.results || []) : (data?.pendientes_tecnicos || []);
  const actaRows = showAllActas ? (actaData?.results || []) : (data?.actas_pendientes_recientes || []);
  const custodyRows = showAllCustody ? (custodyData?.results || []) : (data?.custodios_no_activos_recientes || []);

  return <><div className="itam-dashboard">
    <div className="itam-dashboard-heading">
      <div><span className="itam-dashboard-eyebrow">Inventario TI</span><h2>Resumen de activos</h2><p>Estado actual del maestro de equipos y movimientos registrados en el nuevo módulo.</p></div>
      <button type="button" className="itam-dashboard-refresh" disabled={loading} onClick={refreshDashboard}><RefreshCw size={17} />Actualizar</button>
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
        <h3>Equipos con custodio no activo ({data.conteos.con_custodio_inactivo.toLocaleString('es-CL')})</h3>
        {!data.conteos.con_custodio_inactivo && <p className="itam-dashboard-empty">No hay equipos en esta condición.</p>}
        {(data.conteos.con_custodio_inactivo > 0 || showAllCustody) && <div className="itam-dashboard-pending-heading">
          <p className="itam-dashboard-empty">Incluye colaboradores en licencia, de baja o sin estado registrado. Revise cada caso antes de decidir un movimiento.</p>
          <button type="button" onClick={() => {
            if (showAllCustody) { setShowAllCustody(false); setCustodyData(null); }
            else { setCustodyPage(1); setCustodyLoading(true); setShowAllCustody(true); }
          }}>{showAllCustody ? 'Mostrar recientes' : `Ver todos (${data.conteos.con_custodio_inactivo})`}</button>
        </div>}
        {showAllCustody && custodyLoading && <p role="status">Cargando equipos por revisar...</p>}
        {showAllCustody && custodyError && <p className="itam-dashboard-error" role="alert">{custodyError}</p>}
        <div className="itam-dashboard-recent">
          {custodyRows.map((item) => <article key={item.id}>
            <div><strong>{item.tipo} {item.marca} {item.modelo}</strong><span>Serie: {item.numero_serie || 'N/I'} · AF: {item.af || 'N/I'}</span><span>Custodio: {item.colaborador.nombre_completo} · Estado: {item.colaborador.estado}</span></div>
            <span>{item.estado} · {item.ubicacion_actual}</span>
            <div className="itam-dashboard-actions"><button type="button" onClick={() => onOpenHistory(item)}>Revisar historial</button></div>
          </article>)}
        </div>
        {showAllCustody && custodyData && custodyData.total_pages > 1 && <div className="itam-dashboard-pager">
          <button type="button" disabled={custodyLoading || custodyPage <= 1} onClick={() => changeCustodyPage(custodyPage - 1)}>Anterior</button>
          <span>Página {custodyData.page} de {custodyData.total_pages}</span>
          <button type="button" disabled={custodyLoading || custodyPage >= custodyData.total_pages} onClick={() => changeCustodyPage(custodyPage + 1)}>Siguiente</button>
        </div>}
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
      <section className="itam-dashboard-panel">
        <h3>Actas por firmar ({data.actas_pendientes_firma.toLocaleString('es-CL')})</h3>
        {!data.actas_pendientes_firma && <p className="itam-dashboard-empty">No hay actas pendientes de firma.</p>}
        {(data.actas_pendientes_firma > 0 || showAllActas) && <div className="itam-dashboard-pending-heading">
          <p className="itam-dashboard-empty">Incluye actas generadas y enviadas a firma.</p>
          <button type="button" onClick={() => {
            if (showAllActas) { setShowAllActas(false); setActaData(null); }
            else { setActaPage(1); setActaLoading(true); setShowAllActas(true); }
          }}>{showAllActas ? 'Mostrar recientes' : `Ver todas (${data.actas_pendientes_firma})`}</button>
        </div>}
        {showAllActas && actaLoading && <p role="status">Cargando actas pendientes...</p>}
        {showAllActas && actaError && <p className="itam-dashboard-error" role="alert">{actaError}</p>}
        <div className="itam-dashboard-recent">
          {actaRows.map((acta) => <article key={acta.id}>
            <div><strong>{acta.folio}</strong><span>{acta.tipo_movimiento.replaceAll('_', ' ')} · {acta.estado.replaceAll('_', ' ')}</span></div>
            <time>{new Date(acta.fecha_emision).toLocaleString('es-CL')}</time>
            <div className="itam-dashboard-actions"><button type="button" onClick={() => setGestionActa(acta)}>Gestionar acta</button></div>
          </article>)}
        </div>
        {showAllActas && actaData && actaData.total_pages > 1 && <div className="itam-dashboard-pager">
          <button type="button" disabled={actaLoading || actaPage <= 1} onClick={() => changeActaPage(actaPage - 1)}>Anterior</button>
          <span>Página {actaData.page} de {actaData.total_pages}</span>
          <button type="button" disabled={actaLoading || actaPage >= actaData.total_pages} onClick={() => changeActaPage(actaPage + 1)}>Siguiente</button>
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
  </div>{gestionActa && <ActaGestionModal initialActa={gestionActa} role={role} onClose={() => setGestionActa(null)} onUpdated={refreshDashboard} />}</>;
}
