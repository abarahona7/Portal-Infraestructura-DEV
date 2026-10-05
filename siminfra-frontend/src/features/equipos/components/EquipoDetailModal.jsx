import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import apiClient from '../../../api/client';
import './EquipoDetailModal.css';

export default function EquipoDetailModal({ id, token, onClose, onOpenHistory, revision = 0 }) {
  const [equipo, setEquipo] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id && !token) return undefined;
    const controller = new AbortController();
    const path = id ? `/equipos/${id}/` : `/activos/qr/${token}/`;
    apiClient.get(path, { signal: controller.signal })
      .then(({ data }) => setEquipo(id ? data : data.equipo))
      .catch((err) => { if (err.code !== 'ERR_CANCELED') setError('No se pudo cargar la ficha del equipo.'); });
    return () => controller.abort();
  }, [id, token, revision]);

  if (!id && !token) return null;
  return <div className="equipment-detail-overlay">
    <section className="equipment-detail-modal" role="dialog" aria-modal="true" aria-label="Ficha del equipo">
      <div className="equipment-detail-heading"><h2>Ficha del equipo</h2><button type="button" onClick={onClose} aria-label="Cerrar ficha"><X size={20} /></button></div>
      {error && <p role="alert" className="equipment-detail-error">{error}</p>}
      {!equipo && !error && <p role="status">Cargando ficha...</p>}
      {equipo && <>
        <div className="equipment-detail-identity"><strong>{equipo.tipo} · {equipo.marca} {equipo.modelo}</strong><span>Serie: {equipo.numero_serie || 'Sin registrar'} · Activo fijo: {equipo.af || 'Sin registrar'}</span></div>
        <dl className="equipment-detail-fields">
          <dt>Estado</dt><dd>{equipo.estado}</dd>
          <dt>Departamento</dt><dd>{equipo.departamento_nombre || equipo.departamento || 'Sin departamento asignado'}</dd>
          <dt>Asignado a</dt><dd>{equipo.usuario_nombre || 'Sin usuario asignado'}</dd>
          {equipo.hostname && <><dt>Hostname</dt><dd>{equipo.hostname}</dd></>}
          {equipo.ip_asignada && <><dt>IP asignada</dt><dd>{equipo.ip_asignada}</dd></>}
          {equipo.imei && <><dt>IMEI</dt><dd>{equipo.imei}</dd></>}
          {equipo.numero_telefono && <><dt>Número de teléfono</dt><dd>{equipo.numero_telefono}</dd></>}
          {equipo.accesorios && <><dt>Accesorios</dt><dd>{equipo.accesorios}</dd></>}
        </dl>
        <div className="equipment-detail-footer"><button type="button" onClick={() => onOpenHistory(equipo)}>Ver historial</button></div>
      </>}
    </section>
  </div>;
}
