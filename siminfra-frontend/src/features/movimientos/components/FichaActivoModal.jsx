import { useEffect, useState } from 'react';
import apiClient from '../../../api/client';
import { movimientoError } from '../../../api/movimientosApi';
import MovimientoShell from './MovimientoShell';

const estadoLabel = {
  STOCK: 'Disponible',
  ASIGNADO: 'Asignado',
  PRESTAMO: 'En préstamo',
  MANTENCION: 'En reparación',
  BAJA: 'Dado de baja',
};

export default function FichaActivoModal({ token, onClose, onHistory }) {
  const [asset, setAsset] = useState(null);
  const [qrUrl, setQrUrl] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [error, setError] = useState('');
  const [imageError, setImageError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return undefined;
    const controller = new AbortController();
    apiClient.get(`/activos/qr/${token}/`, { signal: controller.signal })
      .then(({ data }) => {
        setAsset(data.activo);
        setQrUrl(data.qr_url);
        setError('');
      })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') setError(movimientoError(err)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [token]);

  useEffect(() => {
    if (!token) return undefined;
    const controller = new AbortController();
    let url;
    apiClient.get(`/activos/qr/${token}/imagen/`, { responseType: 'blob', signal: controller.signal })
      .then(({ data }) => {
        url = URL.createObjectURL(data);
        setImageUrl(url);
        setImageError('');
      })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') setImageError(movimientoError(err)); });
    return () => {
      controller.abort();
      if (url) URL.revokeObjectURL(url);
    };
  }, [token]);

  if (!token) return null;

  const saveLabel = () => {
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = `activo-${asset.id}-qr.svg`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  return <MovimientoShell title="Ficha del equipo" onClose={onClose} footer={
    <><button className="movimiento-button" onClick={onClose} type="button">Cerrar</button>{asset && <button className="movimiento-button movimiento-button-primary" type="button" onClick={() => { onHistory(asset); onClose(); }}>Ver historial</button>}</>
  }>
    {loading && <p role="status">Cargando ficha...</p>}
    {error && <p className="movimiento-error" role="alert">{error}</p>}
    {asset && <>
      <div className="ficha-asset-identity">
        <strong>{asset.tipo} · {asset.marca} {asset.modelo}</strong>
        <span>Serie: {asset.numero_serie || 'Sin registrar'} · Activo fijo: {asset.af || 'Sin registrar'}</span>
      </div>
      <dl className="movimiento-summary">
        <dt>Estado</dt><dd>{estadoLabel[asset.estado] || asset.estado} · {asset.estado_fisico}</dd>
        <dt>Departamento</dt><dd>{asset.usuario_departamento || 'Sin departamento asignado'}</dd>
        <dt>Asignado a</dt><dd>{asset.usuario_nombre || 'Sin usuario asignado'}</dd>
        {asset.hostname && <><dt>Hostname</dt><dd>{asset.hostname}</dd></>}
        {asset.mac_address && <><dt>MAC</dt><dd>{asset.mac_address}</dd></>}
        {asset.imei && <><dt>IMEI</dt><dd>{asset.imei}</dd></>}
        {asset.numero_telefono && <><dt>Número de teléfono</dt><dd>{asset.numero_telefono}</dd></>}
        {asset.accesorios && <><dt>Accesorios</dt><dd>{asset.accesorios}</dd></>}
        {asset.fecha_vencimiento_garantia && <><dt>Garantía hasta</dt><dd>{asset.fecha_vencimiento_garantia}</dd></>}
      </dl>
      <div className="ficha-asset-qr">
        <strong>Código QR</strong>
        <p className="movimiento-note">La ficha requiere iniciar sesión.</p>
        {imageError && <p className="movimiento-error" role="alert">{imageError}</p>}
        {!imageUrl && !imageError && <p role="status">Cargando código QR...</p>}
        {imageUrl && <><img src={imageUrl} alt={`Código QR del equipo ${asset.id}`} width="160" height="160" /><button className="movimiento-button" type="button" onClick={saveLabel}>Descargar etiqueta SVG</button></>}
        <label>Enlace de la ficha<input readOnly value={qrUrl} onFocus={(event) => event.target.select()} /></label>
      </div>
    </>}
  </MovimientoShell>;
}
