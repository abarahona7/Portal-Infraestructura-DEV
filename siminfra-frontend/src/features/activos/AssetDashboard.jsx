import { useEffect, useRef, useState } from 'react';
import apiClient from '../../api/client';
import './AssetDashboard.css';

const reasons = [
  ['sin_serie', 'SIN NÚMERO DE SERIE', 'sin_serie'],
  ['sin_activo_fijo', 'SIN ACTIVO FIJO', 'sin_activo_fijo'],
  ['sin_custodio', 'SIN USUARIO ASIGNADO', 'sin_custodio'],
  ['custodio_no_activo', 'ASIGNADOS A USUARIOS NO ACTIVOS', 'custodio_no_activo'],
];

export default function AssetDashboard({ onOpenAsset, onEditAsset, revision = 0 }) {
  const [summary, setSummary] = useState(null);
  const [summaryError, setSummaryError] = useState('');
  const [reload, setReload] = useState(0);
  const [selection, setSelection] = useState(null);
  const [page, setPage] = useState(1);
  const [list, setList] = useState(null);
  const [listError, setListError] = useState('');
  const detailRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    apiClient.get('/activos/resumen/', { signal: controller.signal })
      .then(({ data }) => { setSummary(data); setSummaryError(''); })
      .catch((error) => { if (error.code !== 'ERR_CANCELED') setSummaryError('No se pudo cargar el tablero.'); });
    return () => controller.abort();
  }, [reload, revision]);

  useEffect(() => {
    if (!selection) return undefined;
    const controller = new AbortController();
    const params = selection.kind === 'departamento'
      ? { departamento_id: selection.id, page, page_size: 20 }
      : { pendiente: selection.key, page, page_size: 20 };
    apiClient.get('/equipos/', { params, signal: controller.signal })
      .then(({ data }) => { setList(data); setListError(''); })
      .catch((error) => { if (error.code !== 'ERR_CANCELED') setListError('No se pudo cargar la lista de equipos.'); });
    return () => controller.abort();
  }, [selection, page, reload, revision]);

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
  const maxCount = departments[0]?.total || 1;

  return <div className="asset-overview">
    <div className="asset-overview-heading">
      <div><h2>Tablero de activos</h2><p>Estado general y equipos que necesitan revisión.</p></div>
      <button type="button" onClick={() => setReload((value) => value + 1)}>Actualizar</button>
    </div>
    {!summary && !summaryError && <p role="status">Cargando tablero...</p>}
    {summaryError && <p role="alert" className="asset-overview-error">{summaryError}</p>}
    {counts && <>
      <div className="asset-overview-stats" aria-label="Estado de equipos">
        <div><span>Equipos registrados</span><strong>{counts.total}</strong></div>
        <div><span>Con usuario asignado</span><strong>{counts.asignados}</strong></div>
        <div><span>Disponibles</span><strong>{counts.disponibles}</strong></div>
        <div><span>En reparación</span><strong>{counts.reparacion}</strong></div>
        <div><span>Dados de baja</span><strong>{counts.baja}</strong></div>
      </div>
      <section className="asset-overview-card">
        <h3>Departamentos con más equipos asignados</h3>
        {!departments.length && <p>No hay equipos asignados a departamentos.</p>}
        <div className="asset-overview-bars">
          {departments.map((department) => <button type="button" key={department.id}
            aria-expanded={selection?.kind === 'departamento' && selection.id === department.id}
            onClick={() => select({ kind: 'departamento', id: department.id, label: department.nombre })}>
            <span>{department.nombre}</span><span className="asset-overview-track" aria-hidden="true"><span style={{ width: `${department.total / maxCount * 100}%` }} /></span><strong>{department.total}</strong>
          </button>)}
        </div>
      </section>
      <section className="asset-overview-card">
        <h3>Pendientes por revisar</h3>
        <p className="asset-overview-help">Selecciona un motivo para ver los equipos. Los equipos sin usuario asignado pueden estar disponibles, en reparación o dados de baja.</p>
        <div className="asset-overview-reasons">
          {reasons.map(([key, label, countKey]) => <button type="button" key={key}
            aria-expanded={selection?.kind === 'pendiente' && selection.key === key}
            onClick={() => select({ kind: 'pendiente', key, label })}>
            <span>{label}</span><strong>{counts[countKey]}</strong>
          </button>)}
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
            <div><strong>{item.tipo} · {item.marca} {item.modelo}</strong><span>Serie: {item.numero_serie || 'Sin registrar'} · Activo fijo: {item.af || 'Sin registrar'}</span><span>{item.usuario_nombre || 'Sin usuario asignado'} · {item.estado}</span></div>
            <div><button type="button" onClick={(event) => { event.stopPropagation(); onEditAsset(item); }}>Editar</button></div>
          </article>)}
        </div>
        {list.total_pages > 1 && <div className="asset-overview-pages"><button type="button" disabled={page <= 1} onClick={() => { setPage(page - 1); setList(null); }}>Anterior</button><span>Página {list.page} de {list.total_pages}</span><button type="button" disabled={page >= list.total_pages} onClick={() => { setPage(page + 1); setList(null); }}>Siguiente</button></div>}
      </>}
    </section>}
  </div>;
}
