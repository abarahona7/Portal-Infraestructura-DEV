import { useEffect, useState } from 'react';
import apiClient from '../../../api/client';
import { downloadActa, downloadActaFirmada, getMovimientos, movimientoError } from '../../../api/movimientosApi';
import MovimientoShell from './MovimientoShell';

export default function FichaActivoModal({ token, onClose, onHistory }) {
  const [asset, setAsset] = useState(null);
  const [qrUrl, setQrUrl] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [recent, setRecent] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return undefined;
    const controller = new AbortController();
    Promise.all([
      apiClient.get(`/activos/qr/${token}/`, { signal: controller.signal }),
      apiClient.get(`/activos/qr/${token}/imagen/`, { responseType: 'blob', signal: controller.signal }),
    ]).then(([detail, image]) => {
      if (controller.signal.aborted) return;
      setAsset(detail.data.activo);
      setQrUrl(detail.data.qr_url);
      const url = URL.createObjectURL(image.data);
      setImageUrl(url);
      getMovimientos({ activo_id: detail.data.activo.id, page_size: 5 }, controller.signal)
        .then((data) => setRecent(data.results || []))
        .catch((err) => { if (err.code !== 'ERR_CANCELED') setError(movimientoError(err)); });
    }).catch((err) => { if (err.code !== 'ERR_CANCELED') setError(movimientoError(err)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [token]);

  useEffect(() => () => { if (imageUrl) URL.revokeObjectURL(imageUrl); }, [imageUrl]);
  if (!token) return null;
  const saveLabel = () => {
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = `activo-${asset.id}-qr.svg`;
    document.body.appendChild(link); link.click(); link.remove();
  };
  return <MovimientoShell title="Ficha de activo TI" onClose={onClose} footer={
    <><button className="movimiento-button" onClick={onClose} type="button">Cerrar</button>{asset && <button className="movimiento-button movimiento-button-primary" type="button" onClick={() => { onHistory(asset); onClose(); }}>Ver historial completo</button>}</>
  }>
    {loading && <p>Cargando ficha...</p>}
    {error && <p className="movimiento-error" role="alert">{error}</p>}
    {asset && <>
      <dl className="movimiento-summary"><dt>Equipo</dt><dd>{asset.tipo} · {asset.marca} {asset.modelo}</dd><dt>Serie</dt><dd>{asset.numero_serie || 'N/I'}</dd><dt>Activo fijo</dt><dd>{asset.af || 'N/I'}</dd><dt>Estado</dt><dd>{asset.estado} · {asset.estado_fisico}</dd><dt>Asignado a</dt><dd>{asset.usuario_nombre || 'Inventario TI'}</dd><dt>Área</dt><dd>{asset.usuario_departamento || '—'}</dd><dt>Ubicación</dt><dd>{asset.ubicacion_actual || 'N/I'}</dd><dt>Accesorios</dt><dd>{asset.accesorios || 'Sin registro'}</dd><dt>Garantía hasta</dt><dd>{asset.fecha_vencimiento_garantia || 'Sin fecha registrada'}</dd><dt>Observaciones</dt><dd>{recent[0]?.observaciones || 'Sin registro en el último movimiento'}</dd></dl>
      <h4>Etiqueta QR</h4>
      <p className="movimiento-note">El QR contiene solo el enlace opaco de este activo. Para ver la ficha se requiere iniciar sesión.</p>
      {imageUrl && <><img src={imageUrl} alt={`Código QR del activo ${asset.id}`} width="160" height="160" /><p><button className="movimiento-button" type="button" onClick={saveLabel}>Descargar etiqueta SVG</button></p></>}
      <label>Enlace de la ficha<input readOnly value={qrUrl} onFocus={(event) => event.target.select()} /></label>
      <h4>Últimos movimientos</h4>
      {!recent.length && <p className="movimiento-note">Aún no hay movimientos en la nueva trazabilidad.</p>}
      {recent.map((item) => <article className="movimiento-entry" key={item.id}>
        <div className="movimiento-entry-header"><strong>{item.tipo_movimiento}</strong><time>{new Date(item.fecha_movimiento).toLocaleString('es-CL')}</time></div>
        <span>{item.acta ? `Comprobante ${item.acta.folio}` : 'Sin comprobante'} · {item.ejecutado_por}</span>
        {item.acta && <>
          <button type="button" className="movimiento-button" onClick={() => downloadActa(item.acta).catch((err) => setError(movimientoError(err)))}>Descargar comprobante</button>
          {item.acta.tiene_copia_firmada && <button type="button" className="movimiento-button" onClick={() => downloadActaFirmada(item.acta).catch((err) => setError(movimientoError(err)))}>Descargar copia firmada</button>}
        </>}
      </article>)}
    </>}
  </MovimientoShell>;
}
