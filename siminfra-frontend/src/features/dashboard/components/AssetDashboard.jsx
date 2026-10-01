import { useEffect, useState } from 'react';
import { ChevronDown, Download, RefreshCw } from 'lucide-react';
import apiClient from '../../../api/client';
import { downloadActa, downloadActaFirmada, downloadReporteMovimientos, movimientoError } from '../../../api/movimientosApi';
import ActaGestionModal from '../../movimientos/components/ActaGestionModal';
import ActaArchivoPanel from './ActaArchivoPanel';
import './AssetDashboard.css';

const warrantyTabs = [['proximas', 'Próximas'], ['vencidas', 'Vencidas'], ['sin_fecha', 'Sin fecha']];
const unassignedStates = [['', 'Todos'], ['STOCK', 'Disponible'], ['MANTENCION', 'En reparación'], ['BAJA', 'Baja'], ['ASIGNADO', 'Asignado'], ['PRESTAMO', 'En préstamo']];

const warrantyDueLabel = (item) => {
  if (!item.fecha_vencimiento_garantia) return 'Sin fecha de garantía registrada';
  const days = item.dias_para_vencer;
  const remaining = days < 0 ? `${Math.abs(days)} ${days === -1 ? 'día' : 'días'} vencida` : days === 0 ? 'Vence hoy' : `${days} ${days === 1 ? 'día restante' : 'días restantes'}`;
  return `Vencimiento: ${item.fecha_vencimiento_garantia} · ${remaining}`;
};

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
  const [showWarranty, setShowWarranty] = useState(false);
  const [showActas, setShowActas] = useState(false);
  const [warrantyStatus, setWarrantyStatus] = useState('proximas');
  const [showAllWarranty, setShowAllWarranty] = useState(false);
  const [warrantyPage, setWarrantyPage] = useState(1);
  const [warrantyData, setWarrantyData] = useState(null);
  const [warrantyLoading, setWarrantyLoading] = useState(false);
  const [warrantyError, setWarrantyError] = useState('');
  const [reportFrom, setReportFrom] = useState('');
  const [reportTo, setReportTo] = useState('');
  const [reportType, setReportType] = useState('');
  const [reportBusy, setReportBusy] = useState(false);
  const [reportError, setReportError] = useState('');
  const [folioInput, setFolioInput] = useState('');
  const [folioResult, setFolioResult] = useState(null);
  const [folioSearched, setFolioSearched] = useState(false);
  const [folioBusy, setFolioBusy] = useState(false);
  const [folioError, setFolioError] = useState('');

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
    if (!showAllActas) return undefined;
    const controller = new AbortController();
    apiClient.get('/actas/pendientes/', {
      params: { page: actaPage, page_size: 20 }, signal: controller.signal,
    }).then(({ data: response }) => { setActaData(response); setActaError(''); setActaLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setActaError(movimientoError(err)); setActaLoading(false); } });
    return () => controller.abort();
  }, [showAllActas, actaPage, reloadKey]);

  useEffect(() => {
    if (!showAllCustody || !showCustody) return undefined;
    const controller = new AbortController();
    apiClient.get('/activos/custodios-no-activos/', {
      params: { page: custodyPage, page_size: 20 }, signal: controller.signal,
    }).then(({ data: response }) => { setCustodyData(response); setCustodyError(''); setCustodyLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setCustodyError(movimientoError(err)); setCustodyLoading(false); } });
    return () => controller.abort();
  }, [showAllCustody, showCustody, custodyPage, reloadKey]);

  useEffect(() => {
    if (!showAllWarranty) return undefined;
    const controller = new AbortController();
    apiClient.get('/activos/garantias/', {
      params: { estado: warrantyStatus, page: warrantyPage, page_size: 20 }, signal: controller.signal,
    }).then(({ data: response }) => { setWarrantyData(response); setWarrantyError(''); setWarrantyLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setWarrantyError(movimientoError(err)); setWarrantyLoading(false); } });
    return () => controller.abort();
  }, [showAllWarranty, warrantyStatus, warrantyPage, reloadKey]);

  const exportReport = async (event) => {
    event.preventDefault();
    if (reportFrom && reportTo && reportFrom > reportTo) {
      setReportError('La fecha final debe ser igual o posterior a la inicial.');
      return;
    }
    setReportBusy(true);
    setReportError('');
    try {
      await downloadReporteMovimientos({
        ...(reportFrom && { desde: reportFrom }),
        ...(reportTo && { hasta: reportTo }),
        ...(reportType && { tipo_movimiento: reportType }),
      });
    } catch (err) {
      setReportError(movimientoError(err));
    } finally {
      setReportBusy(false);
    }
  };

  const lookupActa = async (folioText) => {
    const folio = folioText.trim().toUpperCase();
    if (!/^ATI-[0-9]{4}-[0-9]{6}$/.test(folio)) {
      setFolioResult(null);
      setFolioSearched(false);
      setFolioError('Indica un folio con formato ATI-AAAA-######.');
      return;
    }
    setFolioBusy(true);
    setFolioError('');
    try {
      const { data: response } = await apiClient.get('/actas/', { params: { folio, page_size: 1 } });
      setFolioResult(response.results?.[0] || null);
      setFolioSearched(true);
    } catch (err) {
      setFolioResult(null);
      setFolioSearched(false);
      setFolioError(movimientoError(err));
    } finally {
      setFolioBusy(false);
    }
  };

  const refreshDashboard = () => {
    setLoading(true);
    if (identifierField) { setIdentifierPage(1); setIdentifierData(null); setIdentifierLoading(true); }
    if (showUnassigned) { setUnassignedPage(1); setUnassignedData(null); setUnassignedLoading(true); }
    if (showAllPending) { setPendingPage(1); setPendingData(null); setPendingLoading(true); }
    if (showAllActas) { setActaPage(1); setActaData(null); setActaLoading(true); }
    if (showAllCustody) { setCustodyPage(1); setCustodyData(null); setCustodyLoading(true); }
    if (showAllWarranty) { setWarrantyPage(1); setWarrantyData(null); setWarrantyLoading(true); }
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
  const toggleWarranty = () => {
    if (!showWarranty && !data.conteos.garantias_proximas) {
      const firstWithResults = data.conteos.garantias_vencidas ? 'vencidas'
        : data.conteos.garantias_sin_fecha ? 'sin_fecha' : 'proximas';
      setWarrantyStatus(firstWithResults);
    }
    setShowWarranty((current) => !current);
  };

  const changeActaPage = (nextPage) => { setActaData(null); setActaLoading(true); setActaPage(nextPage); };
  const changeCustodyPage = (nextPage) => { setCustodyData(null); setCustodyLoading(true); setCustodyPage(nextPage); };
  const changePendingPage = (nextPage) => { setPendingData(null); setPendingLoading(true); setPendingPage(nextPage); };
  const warrantyCount = data?.conteos[`garantias_${warrantyStatus}`] || 0;
  const warrantyRows = showAllWarranty ? (warrantyData?.results || []) :
    (data?.[`garantias_${warrantyStatus}_recientes`] || []);
  const pendingRows = showAllPending ? (pendingData?.results || []) : (data?.pendientes_tecnicos || []);
  const actaRows = showAllActas ? (actaData?.results || []) : (data?.actas_pendientes_recientes || []);
  const custodyRows = showAllCustody ? (custodyData?.results || []) : (data?.custodios_no_activos_recientes || []);
  const reviewItems = data ? [
    ['serie', 'Sin número de serie', data.conteos.sin_serie, () => selectIdentifier('serie')],
    ['activo_fijo', 'Sin activo fijo', data.conteos.sin_activo_fijo, () => selectIdentifier('activo_fijo')],
    ['sin_custodio', 'Sin custodio asignado', data.conteos.sin_custodio, toggleUnassigned],
    ['custodio_inactivo', 'Asignados a colaboradores no activos', data.conteos.con_custodio_inactivo, () => toggleReview('custodio_inactivo')],
    ['fichas', 'Fichas técnicas incompletas', data.conteos.fichas_tecnicas_incompletas, () => toggleReview('fichas')],
  ] : [];
  const visibleReviewItems = reviewItems.filter(([key, , count]) => count > 0 || key === activeReview);

  return <><div className="itam-dashboard">
    <div className="itam-dashboard-heading">
      <div><span className="itam-dashboard-eyebrow">Inventario TI</span><h2>Tablero de activos</h2><p>Primero mira el estado general. Pulsa una fila de «Equipos por revisar» para mostrar su detalle aquí mismo.</p></div>
      <button type="button" className="itam-dashboard-refresh" disabled={loading} onClick={refreshDashboard}><RefreshCw size={17} />Actualizar</button>
    </div>
    {loading && !data && <p role="status">Cargando indicadores...</p>}
    {error && <p className="itam-dashboard-error" role="alert">{error}</p>}
    {data && <>
      <div className="itam-dashboard-view">
      <div className="itam-dashboard-cards">
        {cards.map(([key, label]) => <div className="itam-dashboard-card" key={key}><span>{label}</span><strong>{data.conteos[key].toLocaleString('es-CL')}</strong></div>)}
      </div>
      <div className="itam-dashboard-context">
        <span><strong>{data.movimientos_30_dias.toLocaleString('es-CL')}</strong> movimientos en los últimos 30 días</span>
        <span>Actualizado: {new Date(data.actualizado_en).toLocaleString('es-CL')}</span>
      </div>
      </div>
      <div className="itam-dashboard-view">
      <section className="itam-dashboard-panel itam-dashboard-review">
        <h3>Equipos por revisar</h3>
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
      <div className="itam-dashboard-view">
      <section className="itam-dashboard-panel">
        <div className="itam-dashboard-section-heading"><h3>Garantías</h3><button type="button" aria-expanded={showWarranty} onClick={toggleWarranty}>{showWarranty ? 'Ocultar equipos' : 'Ver equipos'}</button></div>
        <div className="itam-dashboard-warranty-summary">
          <span><strong>{data.conteos.garantias_proximas.toLocaleString('es-CL')}</strong> próximas a vencer</span>
          <span><strong>{data.conteos.garantias_vencidas.toLocaleString('es-CL')}</strong> vencidas</span>
          <span><strong>{data.conteos.garantias_sin_fecha.toLocaleString('es-CL')}</strong> sin fecha registrada</span>
        </div>
        {showWarranty && <>
        <p className="itam-dashboard-empty">Próximas: vencen en los siguientes {data.ventana_garantia_dias} días. No se incluyen equipos dados de baja.</p>
        <div className="itam-dashboard-warranty-controls" role="group" aria-label="Estado de garantía">
          {warrantyTabs.map(([status, label]) => <button key={status} type="button" aria-pressed={warrantyStatus === status} onClick={() => { setWarrantyStatus(status); setWarrantyPage(1); setWarrantyData(null); if (showAllWarranty) setWarrantyLoading(true); }}>{label}</button>)}
        </div>
        {!warrantyCount && <p className="itam-dashboard-empty">No hay activos en esta categoría de garantías.</p>}
        {(warrantyCount > warrantyRows.length || showAllWarranty) && <div className="itam-dashboard-pending-heading">
          <p className="itam-dashboard-empty">{showAllWarranty ? (warrantyStatus === 'sin_fecha' ? 'Lista completa, con los registros más recientes primero.' : 'Lista completa, ordenada por fecha de vencimiento.') : 'Hasta ocho activos por revisar.'}</p>
          <button type="button" onClick={() => {
            if (showAllWarranty) { setShowAllWarranty(false); setWarrantyData(null); }
            else { setWarrantyPage(1); setWarrantyLoading(true); setShowAllWarranty(true); }
          }}>{showAllWarranty ? 'Mostrar recientes' : `Ver todos (${warrantyCount})`}</button>
        </div>}
        {showAllWarranty && warrantyLoading && <p role="status">Cargando garantías...</p>}
        {showAllWarranty && warrantyError && <p className="itam-dashboard-error" role="alert">{warrantyError}</p>}
        <div className="itam-dashboard-recent">
          {warrantyRows.map((item) => <article key={item.id}>
            <div><strong>{item.tipo} {item.marca} {item.modelo}</strong><span>Serie: {item.numero_serie || 'N/I'} · AF: {item.af || 'N/I'}</span><span>{warrantyDueLabel(item)}</span></div>
            <span>{item.estado}</span>
            <div className="itam-dashboard-actions"><button type="button" onClick={() => onEditAsset(item)}>Editar ficha</button><button type="button" onClick={() => onOpenHistory(item)}>Historial</button></div>
          </article>)}
        </div>
        {showAllWarranty && warrantyData && warrantyData.total_pages > 1 && <div className="itam-dashboard-pager">
          <button type="button" disabled={warrantyLoading || warrantyPage <= 1} onClick={() => { setWarrantyData(null); setWarrantyLoading(true); setWarrantyPage(warrantyPage - 1); }}>Anterior</button>
          <span>Página {warrantyData.page} de {warrantyData.total_pages}</span>
          <button type="button" disabled={warrantyLoading || warrantyPage >= warrantyData.total_pages} onClick={() => { setWarrantyData(null); setWarrantyLoading(true); setWarrantyPage(warrantyPage + 1); }}>Siguiente</button>
        </div>}
        </>}
      </section>
      </div>
      <div className="itam-dashboard-view">
      <section className="itam-dashboard-panel">
        <div className="itam-dashboard-section-heading"><h3>Actas pendientes de firma ({data.actas_pendientes_firma.toLocaleString('es-CL')})</h3>{data.actas_pendientes_firma > 0 && <button type="button" aria-expanded={showActas} onClick={() => setShowActas((current) => !current)}>{showActas ? 'Ocultar actas' : 'Ver actas'}</button>}</div>
        {!data.actas_pendientes_firma && <p className="itam-dashboard-empty">No hay actas pendientes de firma.</p>}
        {showActas && data.actas_pendientes_firma > 0 && <>
        {(data.actas_pendientes_firma > actaRows.length || showAllActas) && <div className="itam-dashboard-pending-heading">
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
        </>}
      </section>
      </div>
      <div className="itam-dashboard-view">
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
      </div>
      <div className="itam-dashboard-view">
      <div className="itam-dashboard-extra-heading"><h3>Otras consultas</h3><p>Busca actas, revisa gráficos o descarga una planilla cuando lo necesites.</p></div>
      <details className="itam-dashboard-extra">
        <summary>Buscar actas anteriores o consultar el archivo</summary>
      <section className="itam-dashboard-panel">
        <h3>Buscar acta por folio</h3>
        <p className="itam-dashboard-empty">Consulta un acta emitida, incluso si ya fue firmada, cerrada o anulada.</p>
        <form className="itam-dashboard-report-form" onSubmit={(event) => { event.preventDefault(); lookupActa(folioInput); }}>
          <label>Folio<input type="text" value={folioInput} maxLength={15} placeholder="ATI-2026-000001" disabled={folioBusy} onChange={(event) => { setFolioInput(event.target.value.toUpperCase()); setFolioResult(null); setFolioSearched(false); setFolioError(''); }} /></label>
          <button type="submit" disabled={folioBusy}>{folioBusy ? 'Buscando...' : 'Buscar acta'}</button>
        </form>
        {folioError && <p className="itam-dashboard-error" role="alert">{folioError}</p>}
        {folioSearched && !folioResult && <p className="itam-dashboard-empty" role="status">No se encontró un acta con ese folio.</p>}
        {folioResult && <div className="itam-dashboard-recent"><article>
          <div><strong>{folioResult.folio}</strong><span>{folioResult.tipo_movimiento.replaceAll('_', ' ')} · {folioResult.estado.replaceAll('_', ' ')}</span></div>
          <time>{new Date(folioResult.fecha_emision).toLocaleString('es-CL')}</time>
          <div className="itam-dashboard-actions">
            <button type="button" onClick={() => downloadActa(folioResult).catch((err) => setFolioError(movimientoError(err)))}>Descargar original</button>
            {folioResult.tiene_copia_firmada && <button type="button" onClick={() => downloadActaFirmada(folioResult).catch((err) => setFolioError(movimientoError(err)))}>Copia firmada</button>}
            <button type="button" onClick={() => setGestionActa(folioResult)}>Gestionar acta</button>
          </div>
        </article></div>}
      </section>
      <ActaArchivoPanel role={role} onUpdated={refreshDashboard} />
      </details>
      </div>
      <div className="itam-dashboard-view">
      <details className="itam-dashboard-extra">
        <summary>Ver gráficos por tipo, ubicación y área</summary>
      <div className="itam-dashboard-distributions">
        <Distribution title="Por tipo" items={data.por_tipo} empty="Todavía no hay activos." />
        <Distribution title="Por ubicación" items={data.por_ubicacion} empty="Todavía no hay ubicaciones." />
        <Distribution title="Por área asignada" items={data.por_area} empty="Todavía no hay activos asignados." />
      </div>
      </details>
      </div>
      <div className="itam-dashboard-view">
      <details className="itam-dashboard-extra">
        <summary>Descargar planilla de movimientos</summary>
      <section className="itam-dashboard-panel">
        <h3>Reporte de movimientos</h3>
        <p className="itam-dashboard-empty">Descarga una planilla CSV que puedes abrir en Excel. Si dejas los filtros vacíos, incluye todos los movimientos registrados.</p>
        <form className="itam-dashboard-report-form" onSubmit={exportReport}>
          <label>Desde<input type="date" value={reportFrom} onChange={(event) => setReportFrom(event.target.value)} /></label>
          <label>Hasta<input type="date" value={reportTo} onChange={(event) => setReportTo(event.target.value)} /></label>
          <label>Tipo de movimiento<select value={reportType} onChange={(event) => setReportType(event.target.value)}>
            <option value="">Todos</option>
            <option value="ALTA">Alta</option>
            <option value="ASIGNACION">Asignación</option>
            <option value="REASIGNACION">Reasignación</option>
            <option value="DEVOLUCION">Devolución</option>
            <option value="CAMBIO">Cambio de equipo</option>
            <option value="PRESTAMO">Préstamo</option>
            <option value="INGRESO_REPARACION">Ingreso a reparación</option>
            <option value="SALIDA_REPARACION">Salida de reparación</option>
            <option value="BAJA">Baja</option>
          </select></label>
          <button type="submit" disabled={reportBusy}><Download size={16} />{reportBusy ? 'Preparando planilla...' : 'Descargar planilla CSV'}</button>
        </form>
        {reportError && <p className="itam-dashboard-error" role="alert">{reportError}</p>}
      </section>
      </details>
      </div>
    </>}
  </div>{gestionActa && <ActaGestionModal initialActa={gestionActa} role={role} onClose={() => setGestionActa(null)} onUpdated={() => { refreshDashboard(); if (folioSearched) lookupActa(folioInput); }} />}</>;
}
