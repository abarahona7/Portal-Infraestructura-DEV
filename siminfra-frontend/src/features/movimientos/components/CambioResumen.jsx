import { useEffect, useState } from 'react';
import { downloadActa, getMovimientos, movimientoError } from '../../../api/movimientosApi';

export default function CambioResumen({ operacionId, onClose }) {
  const [movements, setMovements] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    getMovimientos({ operacion_id: operacionId, page_size: 5 }, controller.signal)
      .then((data) => { setMovements(data.results || []); setLoading(false); })
      .catch((err) => { if (err.code !== 'ERR_CANCELED') { setError(movimientoError(err)); setLoading(false); } });
    return () => controller.abort();
  }, [operacionId]);

  return <section className="movimiento-entry" aria-label="Detalle del cambio de equipo">
    <div className="movimiento-entry-header"><h4>Cambio de equipo vinculado</h4><button type="button" className="movimiento-button" onClick={onClose}>Ocultar</button></div>
    {loading && <p>Cargando ambos movimientos...</p>}
    {error && <p className="movimiento-error" role="alert">{error}</p>}
    {!loading && !error && movements.length !== 2 && <p>El cambio no tiene las dos partes esperadas. Revise la trazabilidad.</p>}
    {movements.map((item) => {
      const asset = item.snapshot?.despues || {};
      return <div className="movimiento-operation-part" key={item.id}>
        <strong>{item.tipo_movimiento} · {[asset.tipo, asset.marca, asset.modelo].filter(Boolean).join(' ')}</strong>
        <span>Serie: {asset.numero_serie || 'N/I'} · Estado: {item.estado_operativo_resultante} · Folio: {item.acta?.folio || '—'}</span>
        {item.acta && <button type="button" className="movimiento-button" onClick={() => downloadActa(item.acta).catch((err) => setError(movimientoError(err)))}>Descargar comprobante</button>}
      </div>;
    })}
  </section>;
}
