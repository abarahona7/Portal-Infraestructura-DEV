import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import apiClient from '../../api/client';
import './FichaEquipoQrModal.css';

export default function FichaEquipoQrModal({ token, onClose, onOpenHistory }) {
  const [detail, setDetail] = useState(null);
  const [imageUrl, setImageUrl] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) return undefined;
    const controller = new AbortController();
    apiClient.get(`/activos/qr/${token}/`, { signal: controller.signal })
      .then(({ data }) => setDetail(data))
      .catch((err) => { if (err.code !== 'ERR_CANCELED') setError('No se pudo cargar la ficha del equipo.'); });
    return () => controller.abort();
  }, [token]);

  useEffect(() => {
    if (!token) return undefined;
    const controller = new AbortController();
    let url;
    apiClient.get(`/activos/qr/${token}/imagen/`, { responseType: 'blob', signal: controller.signal })
      .then(({ data }) => { url = URL.createObjectURL(data); setImageUrl(url); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') setError('No se pudo cargar la etiqueta QR.'); });
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url); };
  }, [token]);

  if (!token) return null;
  const equipo = detail?.equipo;
  const download = () => {
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = `equipo-${equipo.id}-qr.svg`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };
  return <div className="asset-qr-overlay">
    <section className="asset-qr-modal" role="dialog" aria-modal="true" aria-label="Ficha del equipo">
      <div className="asset-qr-heading"><h2>Ficha del equipo</h2><button type="button" onClick={onClose} aria-label="Cerrar ficha"><X size={20} /></button></div>
      {error && <p role="alert" className="asset-qr-error">{error}</p>}
      {!equipo && !error && <p role="status">Cargando ficha...</p>}
      {equipo && <>
        <div className="asset-qr-identity"><strong>{equipo.tipo} · {equipo.marca} {equipo.modelo}</strong><span>Serie: {equipo.numero_serie || 'Sin registrar'} · Activo fijo: {equipo.af || 'Sin registrar'}</span></div>
        <dl className="asset-qr-fields">
          <dt>Estado</dt><dd>{equipo.estado}</dd>
          <dt>Departamento</dt><dd>{equipo.departamento || 'Sin departamento asignado'}</dd>
          <dt>Asignado a</dt><dd>{equipo.usuario_nombre || 'Sin usuario asignado'}</dd>
          {equipo.hostname && <><dt>Hostname</dt><dd>{equipo.hostname}</dd></>}
          {equipo.imei && <><dt>IMEI</dt><dd>{equipo.imei}</dd></>}
          {equipo.numero_telefono && <><dt>Número de teléfono</dt><dd>{equipo.numero_telefono}</dd></>}
          {equipo.accesorios && <><dt>Accesorios</dt><dd>{equipo.accesorios}</dd></>}
        </dl>
        <div className="asset-qr-code"><strong>Código QR</strong>{imageUrl && <img src={imageUrl} width="160" height="160" alt={`QR del equipo ${equipo.id}`} />}{imageUrl && <button type="button" onClick={download}>Descargar etiqueta</button>}<span>El enlace requiere iniciar sesión.</span></div>
        <div className="asset-qr-footer"><button type="button" onClick={() => onOpenHistory(equipo)}>Ver historial</button></div>
      </>}
    </section>
  </div>;
}
