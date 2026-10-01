import { useEffect, useState } from 'react';
import { ChevronDown, RefreshCw } from 'lucide-react';
import apiClient from '../../../api/client';
import { movimientoError } from '../../../api/movimientosApi';
import './AssetDashboard.css';

const unassignedStates = [['', 'Todos'], ['STOCK', 'Disponible'], ['MANTENCION', 'En reparación'], ['BAJA', 'Baja'], ['ASIGNADO', 'Asignado'], ['PRESTAMO', 'En préstamo']];

export default function AssetDashboard({ onOpenHistory, onEditAsset }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const [activeReview, setActiveReview] = useState(null);
  const [identifierPage, setIdentifierPage] = useState(1);
  const [identifierData, setIdentifierData] = useState(null);
  const [identifierLoading, setIdentifierLoading] = useState(false);
  const [identifierError, setIdentifierError] = useState('');
  const [unassignedStatus, setUnassignedStatus] = useState('');
  const [unassignedPage, setUnassignedPage] = useState(1);
  const [unassignedData, setUnassignedData] = useState(null);
  const [unassignedLoading, setUnassignedLoading] = useState(false);
  const [unassignedError, setUnassignedError] = useState('');
  const [showAllPending, setShowAllPending] = useState(false);
  const [pendingPage, setPendingPage] = useState(1);
  const [pendingData, setPendingData] = useState(null);
  const [pendingLoading, setPendingLoading] = useState(false);
  const [pendingError, setPendingError] = useState('');
  const [showAllCustody, setShowAllCustody] = useState(false);
  const [custodyPage, setCustodyPage] = useState(1);
  const [custodyData, setCustodyData] = useState(null);
  const [custodyLoading, setCustodyLoading] = useState(false);
  const [custodyError, setCustodyError] = useState('');
  const identifierField = ['serie', 'activo_fijo'].includes(activeReview) ? activeReview : null;
  const showUnassigned = activeReview === 'sin_custodio';
  const showCustody = activeReview === 'custodio_inactivo';
  const showTechnical = activeReview === 'fichas';

  useEffect(() => {
    const controller = new AbortController();
    apiClient.get('/activos/resumen/', { signal: controller.signal })
      .then(({ data: response }) => { setData(response); setError(''); setLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setError(movimientoError(err)); setLoading(false); } });
    return () => controller.abort();
  }, [reloadKey]);

  useEffect(() => {
    if (!identifierField) return undefined;
    const controller = new AbortController();
    apiClient.get('/activos/identificadores-faltantes/', {
      params: { campo: identifierField, page: identifierPage, page_size: 20 }, signal: controller.signal,
    }).then(({ data: response }) => { setIdentifierData(response); setIdentifierError(''); setIdentifierLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setIdentifierError(movimientoError(err)); setIdentifierLoading(false); } });
    return () => controller.abort();
  }, [identifierField, identifierPage, reloadKey]);

  useEffect(() => {
    if (!showUnassigned) return undefined;
    const controller = new AbortController();
    apiClient.get('/activos/sin-custodio/', {
      params: { ...(unassignedStatus && { estado: unassignedStatus }), page: unassignedPage, page_size: 20 },
      signal: controller.signal,
    }).then(({ data: response }) => { setUnassignedData(response); setUnassignedError(''); setUnassignedLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setUnassignedError(movimientoError(err)); setUnassignedLoading(false); } });
    return () => controller.abort();
  }, [showUnassigned, unassignedStatus, unassignedPage, reloadKey]);

  useEffect(() => {
    if (!showAllPending || !showTechnical) return undefined;
    const controller = new AbortController();
    apiClient.get('/activos/pendientes-tecnicos/', {
      params: { page: pendingPage, page_size: 20 }, signal: controller.signal,
    }).then(({ data: response }) => { setPendingData(response); setPendingError(''); setPendingLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setPendingError(movimientoError(err)); setPendingLoading(false); } });
    return () => controller.abort();
  }, [showAllPending, showTechnical, pendingPage, reloadKey]);

  useEffect(() => {
    if (!showAllCustody || !showCustody) return undefined;
    const controller = new AbortController();
    apiClient.get('/activos/custodios-no-activos/', {
      params: { page: custodyPage, page_size: 20 }, signal: controller.signal,
    }).then(({ data: response }) => { setCustodyData(response); setCustodyError(''); setCustodyLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setCustodyError(movimientoError(err)); setCustodyLoading(false); } });
    return () => controller.abort();
  }, [showAllCustody, showCustody, custodyPage, reloadKey]);

  const refreshDashboard = () => {
    setLoading(true);
    if (identifierField) { setIdentifierPage(1); setIdentifierData(null); setIdentifierLoading(true); }
    if (showUnassigned) { setUnassignedPage(1); setUnassignedData(null); setUnassignedLoading(true); }
    if (showAllPending) { setPendingPage(1); setPendingData(null); setPendingLoading(true); }
    if (showAllCustody) { setCustodyPage(1); setCustodyData(null); setCustodyLoading(true); }
    setReloadKey((value) => value + 1);
  };
  const selectIdentifier = (field) => {
    setActiveReview((current) => current === field ? null : field);
    setIdentifierPage(1);
    setIdentifierData(null);
    setIdentifierError('');
    setIdentifierLoading(identifierField !== field);
  };
  const changeIdentifierPage = (nextPage) => { setIdentifierData(null); setIdentifierLoading(true); setIdentifierPage(nextPage); };
  const toggleUnassigned = () => {
    setActiveReview((current) => current === 'sin_custodio' ? null : 'sin_custodio');
    setUnassignedPage(1);
    setUnassignedData(null);
    setUnassignedError('');
    setUnassignedLoading(!showUnassigned);
  };
  const changeUnassignedPage = (nextPage) => { setUnassignedData(null); setUnassignedLoading(true); setUnassignedPage(nextPage); };
  const toggleReview = (target) => setActiveReview((current) => current === target ? null : target);
  const changeCustodyPage = (nextPage) => { setCustodyData(null); setCustodyLoading(true); setCustodyPage(nextPage); };
  const changePendingPage = (nextPage) => { setPendingData(null); setPendingLoading(true); setPendingPage(nextPage); };
  const pendingRows = showAllPending ? (pendingData?.results || []) : (data?.pendientes_tecnicos || []);
  const custodyRows = showAllCustody ? (custodyData?.results || []) : (data?.custodios_no_activos_recientes || []);
  const reviewItems = data ? [
    ['serie', 'Sin número de serie', data.conteos.sin_serie, () => selectIdentifier('serie')],
    ['activo_fijo', 'Sin activo fijo', data.conteos.sin_activo_fijo, () => selectIdentifier('activo_fijo')],
    ['sin_custodio', 'Sin custodio (incluye stock)', data.conteos.sin_custodio, toggleUnassigned],
    ['custodio_inactivo', 'Asignados a colaboradores no activos', data.conteos.con_custodio_inactivo, () => toggleReview('custodio_inactivo')],
    ['fichas', 'Fichas técnicas incompletas', data.conteos.fichas_tecnicas_incompletas, () => toggleReview('fichas')],
  ] : [];
  const visibleReviewItems = reviewItems.filter(([key, , count]) => count > 0 || key === activeReview);
  const topDepartments = (data?.por_area || [])
    .filter((item) => item.nombre !== 'Otros' && item.nombre !== 'Sin registrar')
    .slice(0, 5);
  const largestDepartmentCount = topDepartments[0]?.total || 1;

  return <><div className="itam-dashboard">
    <div className="itam-dashboard-heading">
      <div><span className="itam-dashboard-eyebrow">Inventario de Tecnología</span><h2>Tablero de activos</h2><p>Departamentos con más equipos asignados y pendientes por revisar.</p></div>
      <button type="button" className="itam-dashboard-refresh" disabled={loading} onClick={refreshDashboard}><RefreshCw size={17} />Actualizar</button>
    </div>
    {loading && !data && <p role="status">Cargando indicadores...</p>}
    {error && <p className="itam-dashboard-error" role="alert">{error}</p>}
    {data && <>
      <div className="itam-dashboard-summary">
        <div className="itam-dashboard-panel itam-dashboard-summary-item"><span>Equipos registrados</span><strong>{data.conteos.total.toLocaleString('es-CL')}</strong></div>
        <div className="itam-dashboard-panel itam-dashboard-summary-item"><span>Con colaborador asignado</span><strong>{(data.conteos.total - data.conteos.sin_custodio).toLocaleString('es-CL')}</strong></div>
      </div>
      <section className="itam-dashboard-panel">
        <h3>Departamentos con más equipos asignados</h3>
        <p className="itam-dashboard-empty">Equipos que actualmente tienen un colaborador asignado.</p>
        {!topDepartments.length && <p className="itam-dashboard-empty">No hay departamentos identificados para los equipos asignados.</p>}
        {!!topDepartments.length && <ol className="itam-dashboard-departments" aria-label="Equipos asignados por departamento">
          {topDepartments.map((item) => <li key={item.nombre} className="itam-dashboard-department">
            <div className="itam-dashboard-department-label"><span>{item.nombre}</span><strong>{item.total.toLocaleString('es-CL')} {item.total === 1 ? 'equipo' : 'equipos'}</strong></div>
            <div className="itam-dashboard-department-track" aria-hidden="true"><div className="itam-dashboard-department-bar" style={{ width: `${(item.total / largestDepartmentCount) * 100}%` }} /></div>
          </li>)}
        </ol>}
      </section>
      <div className="itam-dashboard-view">
      <section className="itam-dashboard-panel itam-dashboard-review">
        <h3>Pendientes por revisar</h3>
        <p className="itam-dashboard-empty">Pulsa un motivo para ver los equipos aquí mismo. Un equipo puede aparecer en más de un motivo.</p>
        <div className="itam-dashboard-review-list">
          {!visibleReviewItems.length && <p className="itam-dashboard-empty">No hay equipos pendientes de revisión.</p>}
          {visibleReviewItems.map(([key, label, count, onClick]) => <button key={key} className="itam-dashboard-review-row" type="button" aria-expanded={activeReview === key} onClick={onClick}>
            <span>{label}</span>
            <span className="itam-dashboard-review-count"><strong>{count.toLocaleString('es-CL')}</strong><ChevronDown size={16} aria-hidden="true" /></span>
          </button>)}
        </div>
      </section>
      {identifierField && <section className="itam-dashboard-panel">
        <h3>{identifierField === 'serie' ? 'Equipos sin número de serie' : 'Equipos sin activo fijo'}</h3>
        <p className="itam-dashboard-empty">Incluye todo el maestro, incluso los equipos dados de baja. Revise la ficha antes de completar el identificador.</p>
        {identifierLoading && <p role="status">Cargando equipos...</p>}
        {identifierError && <p className="itam-dashboard-error" role="alert">{identifierError}</p>}
        {identifierData && <>
          <p className="itam-dashboard-empty">{identifierData.count.toLocaleString('es-CL')} equipos encontrados.</p>
          <div className="itam-dashboard-recent">
            {identifierData.results.map((item) => <article key={item.id}>
              <div><strong>{item.tipo} {item.marca} {item.modelo}</strong><span>Serie: {item.numero_serie || 'N/I'} · AF: {item.af || 'N/I'} · ID: {item.id}</span><span>Ubicación: {item.ubicacion_actual}</span></div>
              <span>{item.estado}</span>
              <div className="itam-dashboard-actions"><button type="button" onClick={() => onEditAsset(item)}>Editar ficha</button><button type="button" onClick={() => onOpenHistory(item)}>Historial</button></div>
            </article>)}
          </div>
          {identifierData.total_pages > 1 && <div className="itam-dashboard-pager">
            <button type="button" disabled={identifierLoading || identifierPage <= 1} onClick={() => changeIdentifierPage(identifierPage - 1)}>Anterior</button>
            <span>Página {identifierData.page} de {identifierData.total_pages}</span>
            <button type="button" disabled={identifierLoading || identifierPage >= identifierData.total_pages} onClick={() => changeIdentifierPage(identifierPage + 1)}>Siguiente</button>
          </div>}
        </>}
      </section>}
      {showUnassigned && <section className="itam-dashboard-panel">
        <h3>Activos sin custodio</h3>
        <p className="itam-dashboard-empty">Consulta el inventario sin usuario asignado. Para asignar o cambiar la custodia, registra un nuevo movimiento.</p>
        <div className="itam-dashboard-report-form">
          <label>Estado operativo<select value={unassignedStatus} onChange={(event) => { setUnassignedStatus(event.target.value); setUnassignedPage(1); setUnassignedData(null); setUnassignedLoading(true); }}>
            {unassignedStates.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></label>
        </div>
        {unassignedLoading && <p role="status">Cargando activos...</p>}
        {unassignedError && <p className="itam-dashboard-error" role="alert">{unassignedError}</p>}
        {unassignedData && <>
          <p className="itam-dashboard-empty">{unassignedData.count.toLocaleString('es-CL')} activos encontrados.</p>
          <div className="itam-dashboard-recent">
            {unassignedData.results.map((item) => <article key={item.id}>
              <div><strong>{item.tipo} {item.marca} {item.modelo}</strong><span>Serie: {item.numero_serie || 'N/I'} · AF: {item.af || 'N/I'} · ID: {item.id}</span><span>Ubicación: {item.ubicacion_actual}</span></div>
              <span>{item.estado}</span>
              <div className="itam-dashboard-actions"><button type="button" onClick={() => onOpenHistory(item)}>Historial</button><button type="button" onClick={() => onEditAsset(item)}>Editar ficha</button></div>
            </article>)}
          </div>
          {unassignedData.total_pages > 1 && <div className="itam-dashboard-pager">
            <button type="button" disabled={unassignedLoading || unassignedPage <= 1} onClick={() => changeUnassignedPage(unassignedPage - 1)}>Anterior</button>
            <span>Página {unassignedData.page} de {unassignedData.total_pages}</span>
            <button type="button" disabled={unassignedLoading || unassignedPage >= unassignedData.total_pages} onClick={() => changeUnassignedPage(unassignedPage + 1)}>Siguiente</button>
          </div>}
        </>}
      </section>}
      </div>
      {showCustody && <div className="itam-dashboard-view">
      <section className="itam-dashboard-panel">
        <h3>Equipos con custodio no activo ({data.conteos.con_custodio_inactivo.toLocaleString('es-CL')})</h3>
        {!data.conteos.con_custodio_inactivo && <p className="itam-dashboard-empty">No hay equipos en esta condición.</p>}
        {(data.conteos.con_custodio_inactivo > custodyRows.length || showAllCustody) && <div className="itam-dashboard-pending-heading">
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
      </div>}
      {showTechnical && <div className="itam-dashboard-view">
      <section className="itam-dashboard-panel">
        <h3>Fichas técnicas por completar</h3>
        <p className="itam-dashboard-empty">Incluye {data.conteos.sin_imei_celular.toLocaleString('es-CL')} celulares sin IMEI, {data.conteos.sin_hostname_computador.toLocaleString('es-CL')} computadores sin hostname y {data.conteos.sin_mac_computador.toLocaleString('es-CL')} sin MAC. Un equipo puede tener más de un dato pendiente.</p>
        {!data.conteos.fichas_tecnicas_incompletas && <p className="itam-dashboard-empty">No hay fichas técnicas pendientes en activos vigentes.</p>}
        {(data.conteos.fichas_tecnicas_incompletas > pendingRows.length || showAllPending) && <div className="itam-dashboard-pending-heading">
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
      </div>}
    </>}
  </div></>;
}
