import { useEffect, useRef, useState } from 'react';
import {
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  HardDrive,
  Info,
  Keyboard,
  Laptop,
  Layers3,
  Monitor,
  Package,
  PowerOff,
  Router,
  ShieldCheck,
  Smartphone,
  Tablet,
  Users,
} from 'lucide-react';
import apiClient from '../../api/client';
import { getApiErrorMessage } from '../../utils/apiErrorMessage';
import { formatEquipmentTypeLabel } from '../../utils/formatEquipmentType';
import './AssetDashboard.css';

const reviewReasons = [
  { key: 'custodio_baja', label: 'Asignados a usuarios de baja', level: 'urgente', help: 'Revisar a quién corresponde el equipo.' },
  { key: 'sin_serie', label: 'Sin número de serie', level: 'datos', help: 'Completar el identificador cuando esté disponible.' },
  { key: 'sin_activo_fijo', label: 'Sin activo fijo', level: 'datos', help: 'Completarlo cuando corresponda al equipo.' },
  { key: 'sin_custodio', label: 'Sin usuario asignado', level: 'informativo', help: 'Puede estar en stock o dado de baja.' },
];

const typeIcons = {
  Notebook: Laptop,
  Celular: Smartphone,
  Tablet,
  Mac: Monitor,
  'BAM / Router': Router,
};

const peripheralTypes = new Set([
  'Monitor', 'Adaptador', 'Audífonos', 'Teclado', 'Mouse', 'Docking', 'Otro Periférico',
]);

const getTypeIcon = (type) => typeIcons[type] || (peripheralTypes.has(type) ? Keyboard : Package);

export default function AssetDashboard({ onOpenAsset, onEditAsset, revision = 0 }) {
  const [summary, setSummary] = useState(null);
  const [summaryError, setSummaryError] = useState('');
  const [lastUpdatedAt, setLastUpdatedAt] = useState(null);
  const [syncedRevision, setSyncedRevision] = useState(null);
  const [selection, setSelection] = useState(null);
  const [page, setPage] = useState(1);
  const [list, setList] = useState(null);
  const [listError, setListError] = useState('');
  const [highlightedDepartment, setHighlightedDepartment] = useState(null);
  const detailRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    apiClient.get('/activos/resumen/', { signal: controller.signal })
      .then(({ data }) => {
        if (controller.signal.aborted) return;
        setSummary(data);
        setSummaryError('');
        setLastUpdatedAt(new Date());
      })
      .catch((error) => {
        if (!controller.signal.aborted && error.code !== 'ERR_CANCELED') {
          setSummaryError(getApiErrorMessage(error, 'No se pudo cargar el tablero.'));
        }
      })
      .finally(() => { if (!controller.signal.aborted) setSyncedRevision(revision); });
    return () => controller.abort();
  }, [revision]);

  useEffect(() => {
    if (!selection) return undefined;
    const controller = new AbortController();
    const filters = selection.kind === 'departamento'
      ? { departamento_id: selection.id }
      : selection.kind === 'tipo'
        ? { tipo: selection.id }
        : selection.kind === 'estado'
          ? { estado: selection.id }
          : selection.kind === 'asignados'
            ? { asignado: 'si' }
            : selection.kind === 'pendiente'
              ? { pendiente: selection.key }
              : {};
    const params = { ...filters, page, page_size: 20 };
    apiClient.get('/equipos/', { params, signal: controller.signal })
      .then(({ data }) => { setList(data); setListError(''); })
      .catch((error) => {
        if (error.code !== 'ERR_CANCELED') {
          setListError(getApiErrorMessage(error, 'No se pudo cargar la lista de equipos.'));
        }
      });
    return () => controller.abort();
  }, [selection, page, revision]);

  useEffect(() => {
    if (selection) detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [selection]);

  const select = (next) => {
    setSelection((current) => current?.kind === next.kind && current?.id === next.id && current?.key === next.key ? null : next);
    setPage(1);
    setList(null);
    setListError('');
  };
  const counts = summary?.conteos;
  const departments = summary?.departamentos || [];
  const types = summary?.tipos || [];
  const visibleReasons = counts
    ? reviewReasons.filter(({ key }) => (counts[key] || 0) > 0)
    : [];
  const maxCount = Math.max(1, ...departments.map((department) => department.total));
  const refreshing = syncedRevision !== revision;
  const stats = [
    { kind: 'todos', id: null, label: 'Equipos registrados', count: counts?.total, icon: Package, tone: 'blue' },
    { kind: 'asignados', id: null, label: 'Con usuario asignado', count: counts?.asignados, icon: Users, tone: 'green' },
    { kind: 'estado', id: 'STOCK', label: 'Disponibles', count: counts?.disponibles, icon: HardDrive, tone: 'violet' },
    { kind: 'estado', id: 'BAJA', label: 'Dados de baja', count: counts?.baja, icon: PowerOff, tone: 'orange' },
  ];

  return <div className="asset-overview">
    <div className="asset-overview-heading">
      <div><h2>Tablero de activos</h2><p>Estado general y equipos que necesitan revisión.</p></div>
      <div className="asset-overview-sync">
        <small role="status" aria-live="polite">
          {refreshing
            ? 'Sincronizando cambios...'
            : lastUpdatedAt
              ? <>Actualización automática · Última sincronización: <time dateTime={lastUpdatedAt.toISOString()}>{lastUpdatedAt.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time></>
              : 'Esperando sincronización automática'}
        </small>
      </div>
    </div>
    {!summary && !summaryError && <p role="status">Cargando tablero...</p>}
    {summaryError && <p role="alert" className="asset-overview-error">{summaryError}</p>}
    {counts && <>
      <div className="asset-overview-main">
        <section className="asset-overview-card asset-overview-chart" aria-label="Gráfico de equipos por departamento">
          <div className="asset-overview-chart-heading">
            <span className="asset-overview-heading-icon asset-overview-heading-icon--blue"><Layers3 size={21} /></span>
            <div><h3>Equipos asignados por departamento</h3>
              <p className="asset-overview-help">
                {highlightedDepartment
                  ? `${highlightedDepartment.nombre}: ${highlightedDepartment.total} ${highlightedDepartment.total === 1 ? 'equipo' : 'equipos'}`
                  : 'Distribución actual de equipos por área.'}
              </p>
            </div>
          </div>
          {!departments.length && <p>No hay departamentos registrados.</p>}
          <div className="asset-overview-bars" role="group" aria-label="Equipos asignados por departamento">
            {departments.map((department) => <button type="button" key={department.id}
              className="asset-overview-bar"
              style={{ '--bar-width': `${department.total / maxCount * 100}%` }}
              aria-label={`${department.nombre}: ${department.total} ${department.total === 1 ? 'equipo' : 'equipos'}`}
              aria-expanded={selection?.kind === 'departamento' && selection.id === department.id}
              title={`${department.nombre}: ${department.total} ${department.total === 1 ? 'equipo' : 'equipos'}`}
              onMouseEnter={() => setHighlightedDepartment(department)}
              onMouseLeave={() => setHighlightedDepartment(null)}
              onFocus={() => setHighlightedDepartment(department)}
              onBlur={() => setHighlightedDepartment(null)}
              onClick={() => select({ kind: 'departamento', id: department.id, label: department.nombre })}>
              <span className="asset-overview-bar-name" aria-hidden="true">{department.nombre}</span>
              <span className="asset-overview-bar-plot" aria-hidden="true"><span className="asset-overview-bar-fill" /></span>
              <strong className="asset-overview-bar-value">{department.total}</strong>
            </button>)}
          </div>
        </section>
        <div className="asset-overview-stats" aria-label="Estado de equipos">
          {stats.map(({ kind, id, label, count, icon: Icon, tone }) => <button type="button" key={label}
            className={`asset-overview-stat asset-overview-stat--${tone}`}
            aria-label={`${label}: ${count}. Ver equipos`}
            aria-expanded={selection?.kind === kind && selection?.id === id}
            onClick={() => select({ kind, id, label })}>
            <span className="asset-overview-stat-icon"><Icon size={22} /></span>
            <span className="asset-overview-stat-label">{label}</span>
            <strong>{count}</strong>
            <small>Ver equipos <ChevronRight size={14} /></small>
          </button>)}
        </div>
      </div>
      {types.length > 0 && <section className="asset-overview-card asset-overview-types">
        <div className="asset-overview-section-heading">
          <div className="asset-overview-section-title"><span className="asset-overview-heading-icon asset-overview-heading-icon--blue"><Package size={21} /></span><div><h3>Inventario por tipo</h3><p className="asset-overview-help">Resumen de equipos por categoría.</p></div></div>
          <p className="asset-overview-section-action">Selecciona un tipo para ver sus equipos <ChevronRight size={15} /></p>
        </div>
        <div className="asset-overview-type-grid">
          {types.map((item) => {
            const TypeIcon = getTypeIcon(item.tipo);
            return <button type="button" key={item.tipo}
              aria-expanded={selection?.kind === 'tipo' && selection.id === item.tipo}
              onClick={() => select({ kind: 'tipo', id: item.tipo, label: formatEquipmentTypeLabel(item.tipo) })}>
              <span className="asset-overview-type-icon"><TypeIcon size={23} /></span>
              <span className="asset-overview-type-content"><span>{formatEquipmentTypeLabel(item.tipo)}</span><strong>{item.total}</strong><small>{item.asignados} con usuario</small></span>
              <ChevronRight className="asset-overview-type-arrow" size={18} />
            </button>;
          })}
        </div>
      </section>}
      <section className="asset-overview-card">
        <div className="asset-overview-section-heading">
          <div className="asset-overview-section-title"><span className="asset-overview-heading-icon asset-overview-heading-icon--blue"><ShieldCheck size={21} /></span><div><h3>Atención y revisión</h3>{counts.custodio_baja === 0 && <p className="asset-overview-ok"><CheckCircle2 size={14} /> Sin equipos asignados a usuarios de baja.</p>}</div></div>
          <p className="asset-overview-help">La asignación a una persona de baja requiere revisión. Los datos incompletos y los equipos sin usuario se muestran por separado.</p>
        </div>
        {visibleReasons.length === 0 && <p className="asset-overview-help">No hay equipos pendientes de revisión.</p>}
        <div className="asset-overview-reasons">
          {visibleReasons.map(({ key, label, level, help }) => {
            const ReasonIcon = level === 'urgente' || level === 'datos' ? CircleAlert : Info;
            return <button type="button" key={key} className={`asset-overview-reason asset-overview-reason--${level}`}
              aria-expanded={selection?.kind === 'pendiente' && selection.key === key}
              onClick={() => select({ kind: 'pendiente', key, label })}>
              <ReasonIcon size={18} /><span><b>{label}</b><small>{help}</small></span><strong>{counts[key]}</strong><ChevronRight size={17} />
            </button>;
          })}
        </div>
      </section>
    </>}
    {selection && <section ref={detailRef} className="asset-overview-card asset-overview-detail">
      <div className="asset-overview-detail-heading"><h3>{selection.label}</h3><button type="button" onClick={() => setSelection(null)}>Cerrar</button></div>
      {listError && <p role="alert" className="asset-overview-error">{listError}</p>}
      {!list && !listError && <p role="status">Cargando equipos...</p>}
      {list && <>
        <p className="asset-overview-help">{list.count} equipos · Pulsa un equipo para ver su ficha.</p>
        <div className="asset-overview-items">
          {list.results.map((item) => <article key={item.id}
            onClick={() => onOpenAsset(item)}
            onKeyDown={(event) => {
              if (event.target === event.currentTarget && (event.key === 'Enter' || event.key === ' ')) {
                event.preventDefault();
                onOpenAsset(item);
              }
            }}
            role="button" tabIndex={0}
            aria-label={`Abrir ficha de ${item.marca || ''} ${item.modelo || ''}`.trim()}>
            <div><strong>{formatEquipmentTypeLabel(item.tipo)} · {item.marca} {item.modelo}</strong><span>Serie: {item.numero_serie || 'Sin registrar'} · Activo fijo: {item.af || 'Sin registrar'}</span><span>{item.usuario_nombre || 'Sin usuario asignado'} · {item.estado}</span></div>
            <div><button type="button" onClick={(event) => { event.stopPropagation(); onEditAsset(item); }}>Editar</button></div>
          </article>)}
        </div>
        {list.total_pages > 1 && <div className="asset-overview-pages"><button type="button" disabled={page <= 1} onClick={() => { setPage(page - 1); setList(null); }}>Anterior</button><span>Página {list.page} de {list.total_pages}</span><button type="button" disabled={page >= list.total_pages} onClick={() => { setPage(page + 1); setList(null); }}>Siguiente</button></div>}
      </>}
    </section>}
  </div>;
}
