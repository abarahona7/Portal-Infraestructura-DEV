import { useEffect, useState } from 'react';
import apiClient from '../../api/client';
import { getApiErrorMessage } from '../../utils/apiErrorMessage';
import './BajaReviewsPage.css';

const resourceLabel = { equipo: 'Equipo', ip: 'Dirección IP', anexo: 'Anexo' };

export default function BajaReviewsPage({ revision, onOpenResource, onCountChange, showToast }) {
  const [status, setStatus] = useState('pendientes');
  const [page, setPage] = useState(1);
  const [response, setResponse] = useState(null);
  const [checked, setChecked] = useState({});
  const [saving, setSaving] = useState(null);
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    apiClient.get('/revisiones-baja/', { params: { estado: status, page }, signal: controller.signal })
      .then(({ data }) => { setResponse(data); setError(''); onCountChange(data.pendientes); })
      .catch((err) => {
        if (err.code !== 'ERR_CANCELED') {
          setError(getApiErrorMessage(err, 'No se pudieron cargar las revisiones.'));
        }
      });
    return () => controller.abort();
  }, [status, page, revision, reload, onCountChange]);

  const confirm = async (item) => {
    const confirmations = item.recursos.map((resource) => resource.clave);
    if (!confirmations.every((key) => checked[item.id]?.[key])) return;
    setSaving(item.id);
    try {
      await apiClient.post(`/revisiones-baja/${item.id}/confirmar/`, { confirmaciones: confirmations });
      setChecked((current) => { const next = { ...current }; delete next[item.id]; return next; });
      setReload((value) => value + 1);
      showToast('Revisión registrada en el historial del usuario.');
    } catch (err) {
      showToast(getApiErrorMessage(err, 'No se pudo confirmar la revisión.'), 'error');
      setReload((value) => value + 1);
    } finally {
      setSaving(null);
    }
  };

  return <section className="baja-reviews" aria-label="Revisiones de recursos liberados">
    <div className="baja-reviews-heading">
      <div><h2>Recursos liberados</h2><p>Revisa los cambios por Baja o Licencia Médica. Abre cada registro y confirma que quedó correctamente liberado.</p></div>
      <div className="baja-reviews-tabs" role="group" aria-label="Estado de revisión">
        <button type="button" className={status === 'pendientes' ? 'is-active' : ''} onClick={() => { setStatus('pendientes'); setPage(1); }}>Pendientes ({response?.pendientes ?? 0})</button>
        <button type="button" className={status === 'revisadas' ? 'is-active' : ''} onClick={() => { setStatus('revisadas'); setPage(1); }}>Revisadas</button>
      </div>
    </div>
    {error && <p role="alert" className="baja-reviews-error">{error} <button type="button" onClick={() => setReload((value) => value + 1)}>Reintentar</button></p>}
    {!error && !response && <p>Cargando revisiones...</p>}
    {!error && response?.results.length === 0 && <p className="baja-reviews-empty">{status === 'pendientes' ? 'No hay liberaciones pendientes de revisión.' : 'Aún no hay revisiones finalizadas.'}</p>}
    {!error && response?.results.map((item) => {
      const allChecked = item.recursos.every((resource) => checked[item.id]?.[resource.clave]);
      return <article className="baja-review-card" key={item.id}>
        <div className="baja-review-title"><div><h3>{item.usuario_nombre}</h3><span>{item.usuario_red} · {item.motivo === 'LICENCIA' ? 'Licencia médica' : 'Baja'} registrada {new Date(item.creado_en).toLocaleString('es-CL')}</span></div><strong>{item.recursos.length} {item.recursos.length === 1 ? 'recurso' : 'recursos'}</strong></div>
        <ul className="baja-review-resources">{item.recursos.map((resource) => <li key={resource.clave}>
          {status === 'pendientes' && <label className="baja-review-check"><input type="checkbox" checked={Boolean(checked[item.id]?.[resource.clave])} onChange={(event) => setChecked((current) => ({ ...current, [item.id]: { ...current[item.id], [resource.clave]: event.target.checked } }))} aria-label={`Confirmar ${resourceLabel[resource.tipo]} ${resource.nombre}`} /></label>}
          <div className="baja-review-resource"><b>{resourceLabel[resource.tipo]}: {resource.nombre}</b><small>{resource.detalle}</small></div>
          <button type="button" onClick={() => onOpenResource(resource)}>Ver historial</button>
        </li>)}</ul>
        <div className="baja-review-footer">{item.revisado_en ? <span>Revisado por {item.revisado_por} · {new Date(item.revisado_en).toLocaleString('es-CL')}</span> : <><span>La alerta seguirá pendiente hasta confirmar todos los recursos.</span><button type="button" disabled={!allChecked || saving === item.id} onClick={() => confirm(item)}>{saving === item.id ? 'Guardando...' : 'Confirmar revisión'}</button></>}</div>
      </article>;
    })}
    {response && response.count > response.page_size && <div className="baja-reviews-pagination"><button type="button" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>Anterior</button><span>Página {page} de {Math.ceil(response.count / response.page_size)}</span><button type="button" disabled={page * response.page_size >= response.count} onClick={() => setPage((value) => value + 1)}>Siguiente</button></div>}
  </section>;
}
