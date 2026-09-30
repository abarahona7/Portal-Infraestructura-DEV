import { useEffect, useState } from 'react';
import { cambiarEstadoActa, downloadActa, downloadActaFirmada, getActaEventos, movimientoError } from '../../../api/movimientosApi';
import MovimientoShell from './MovimientoShell';

const nextState = { GENERADA: 'PENDIENTE_FIRMA', PENDIENTE_FIRMA: 'FIRMADA', FIRMADA: 'CERRADA' };
const labels = { PENDIENTE_FIRMA: 'Enviar a firma', FIRMADA: 'Registrar copia firmada', CERRADA: 'Cerrar acta', ANULADA: 'Anular acta' };

export default function ActaGestionModal({ initialActa, role, onClose, onUpdated }) {
  const [acta, setActa] = useState(initialActa);
  const [eventos, setEventos] = useState([]);
  const [nuevoEstado, setNuevoEstado] = useState(nextState[initialActa.estado] || (role === 'Administrador' && initialActa.estado !== 'ANULADA' ? 'ANULADA' : ''));
  const [motivo, setMotivo] = useState('');
  const [archivo, setArchivo] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    getActaEventos(initialActa.id, controller.signal).then(setEventos)
      .catch((err) => { if (err.code !== 'ERR_CANCELED') setError(movimientoError(err)); });
    return () => controller.abort();
  }, [initialActa.id]);

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      const updated = await cambiarEstadoActa(acta.id, nuevoEstado, motivo, archivo);
      setActa(updated);
      setNuevoEstado(nextState[updated.estado] || (role === 'Administrador' && updated.estado !== 'ANULADA' ? 'ANULADA' : ''));
      setMotivo('');
      setArchivo(null);
      setEventos(await getActaEventos(acta.id));
      onUpdated();
    } catch (err) { setError(movimientoError(err)); }
    finally { setBusy(false); }
  };

  return <MovimientoShell title={`Acta ${acta.folio}`} onClose={onClose} busy={busy} footer={<button type="button" className="movimiento-button" onClick={onClose} disabled={busy}>Cerrar</button>}>
    <p className="movimiento-note">Estado actual: <strong>{acta.estado.replaceAll('_', ' ')}</strong>. El PDF original permanece disponible y no se modifica al gestionar el acta.</p>
    <div className="movimiento-add">
      <button type="button" className="movimiento-button" onClick={() => downloadActa(acta).catch((err) => setError(movimientoError(err)))}>Descargar original</button>
      {acta.tiene_copia_firmada && <button type="button" className="movimiento-button" onClick={() => downloadActaFirmada(acta).catch((err) => setError(movimientoError(err)))}>Descargar copia firmada</button>}
    </div>
    <h4>Historial de estados</h4>
    {eventos.length === 0 && <p className="movimiento-note">Acta generada; todavía no hay transiciones.</p>}
    {eventos.map((item) => <article className="movimiento-entry" key={item.id}>
      <strong>{item.estado_anterior.replaceAll('_', ' ')} → {item.estado_nuevo.replaceAll('_', ' ')}</strong>
      <span>{new Date(item.fecha).toLocaleString('es-CL')} · {item.usuario_nombre || `Usuario #${item.usuario_id}`}</span>
      {item.motivo && <span>Motivo: {item.motivo}</span>}
      {item.hash_copia_firmada && <span>Huella SHA-256 de la copia: {item.hash_copia_firmada}</span>}
    </article>)}
    {error && <p className="movimiento-error" role="alert">{error}</p>}
    {(nextState[acta.estado] || (role === 'Administrador' && acta.estado !== 'ANULADA')) && <form onSubmit={submit} className="movimiento-entry">
      <label>Acción
        <select value={nuevoEstado} onChange={(event) => { setNuevoEstado(event.target.value); setArchivo(null); }} required>
          {nextState[acta.estado] && <option value={nextState[acta.estado]}>{labels[nextState[acta.estado]]}</option>}
          {role === 'Administrador' && acta.estado !== 'ANULADA' && <option value="ANULADA">Anular acta</option>}
        </select>
      </label>
      {nuevoEstado === 'FIRMADA' && <label>Copia PDF firmada manualmente (máximo 10 MB)
        <input type="file" accept="application/pdf,.pdf" required onChange={(event) => setArchivo(event.target.files?.[0] || null)} />
      </label>}
      {nuevoEstado === 'FIRMADA' && <p className="movimiento-note">El portal conserva esta copia y su huella, pero no comprueba la autenticidad de la firma.</p>}
      {nuevoEstado === 'ANULADA' && <label>Motivo de anulación
        <textarea value={motivo} maxLength={2000} required onChange={(event) => setMotivo(event.target.value)} />
      </label>}
      <button className="movimiento-button movimiento-button-primary" type="submit" disabled={busy}>{busy ? 'Guardando...' : labels[nuevoEstado]}</button>
    </form>}
  </MovimientoShell>;
}
