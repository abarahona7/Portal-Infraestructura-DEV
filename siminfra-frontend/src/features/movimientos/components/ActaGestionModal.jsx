import { useEffect, useState } from 'react';
import { cambiarEstadoActa, downloadActa, downloadActaFirmada, getActaEventos, movimientoError, verificarIntegridadActa } from '../../../api/movimientosApi';
import MovimientoShell from './MovimientoShell';

const nextState = { GENERADA: 'PENDIENTE_FIRMA', PENDIENTE_FIRMA: 'FIRMADA', FIRMADA: 'CERRADA' };
const labels = { PENDIENTE_FIRMA: 'Enviar a firma', FIRMADA: 'Registrar copia firmada', CERRADA: 'Cerrar acta', ANULADA: 'Anular acta' };
const stateLabels = { GENERADA: 'Generada', PENDIENTE_FIRMA: 'Pendiente de firma', FIRMADA: 'Firmada', CERRADA: 'Cerrada', ANULADA: 'Anulada' };

export default function ActaGestionModal({ initialActa, role, onClose, onUpdated }) {
  const [acta, setActa] = useState(initialActa);
  const [eventos, setEventos] = useState([]);
  const [nuevoEstado, setNuevoEstado] = useState(nextState[initialActa.estado] || (role === 'Administrador' && initialActa.estado !== 'ANULADA' ? 'ANULADA' : ''));
  const [motivo, setMotivo] = useState('');
  const [archivo, setArchivo] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(false);
  const [integridad, setIntegridad] = useState(null);

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
      setIntegridad(null);
      setEventos(await getActaEventos(acta.id));
      onUpdated();
    } catch (err) { setError(movimientoError(err)); }
    finally { setBusy(false); }
  };

  const checkIntegrity = async () => {
    setChecking(true);
    setError('');
    try { setIntegridad(await verificarIntegridadActa(acta.id)); }
    catch (err) { setIntegridad(null); setError(movimientoError(err)); }
    finally { setChecking(false); }
  };

  const nextAction = nextState[acta.estado];
  const canAnular = role === 'Administrador' && acta.estado !== 'ANULADA';

  return <MovimientoShell title={`Acta ${acta.folio}`} onClose={onClose} busy={busy} footer={<button type="button" className="movimiento-button" onClick={onClose} disabled={busy}>Cerrar</button>}>
    <p className="movimiento-note">Situación actual: <strong>{stateLabels[acta.estado] || acta.estado}</strong>. El acta se generó automáticamente al registrar el movimiento.</p>
    <div className="movimiento-add">
      <button type="button" className="movimiento-button" onClick={() => downloadActa(acta).catch((err) => setError(movimientoError(err)))}>Descargar acta PDF</button>
      {acta.tiene_copia_firmada && <button type="button" className="movimiento-button" onClick={() => downloadActaFirmada(acta).catch((err) => setError(movimientoError(err)))}>Descargar copia firmada</button>}
    </div>
    {error && <p className="movimiento-error" role="alert">{error}</p>}
    {(nextAction || canAnular) && <form onSubmit={submit} className="movimiento-entry">
      {nextAction && canAnular && <label>Acción
        <select value={nuevoEstado} onChange={(event) => { setNuevoEstado(event.target.value); setArchivo(null); }} required>
          <option value={nextAction}>{labels[nextAction]}</option>
          <option value="ANULADA">Anular acta</option>
        </select>
      </label>}
      {nuevoEstado === 'FIRMADA' && <label>Subir copia PDF firmada (máximo 10 MB)
        <input type="file" accept="application/pdf,.pdf" required onChange={(event) => setArchivo(event.target.files?.[0] || null)} />
      </label>}
      {nuevoEstado === 'FIRMADA' && <p className="movimiento-note">La copia firmada quedará guardada junto al acta original.</p>}
      {nuevoEstado === 'ANULADA' && <label>Motivo de anulación
        <textarea value={motivo} maxLength={2000} required onChange={(event) => setMotivo(event.target.value)} />
      </label>}
      <button className="movimiento-button movimiento-button-primary" type="submit" disabled={busy}>{busy ? 'Guardando...' : labels[nuevoEstado]}</button>
    </form>}
    <details className="movimiento-acta-details">
      <summary>Ver historial y comprobación de archivos</summary>
      <p className="movimiento-note">El PDF original permanece guardado sin cambios. Esta comprobación revisa los archivos, pero no certifica la identidad de quien firmó.</p>
      <button type="button" className="movimiento-button" disabled={checking} onClick={checkIntegrity}>{checking ? 'Comprobando...' : 'Comprobar archivos'}</button>
      {integridad && <div className="movimiento-entry" role="status">
        <strong>Resultado de la comprobación</strong>
        <span>PDF original: {integridad.original.coincide ? 'archivo íntegro' : 'archivo faltante o modificado'}.</span>
        <span>Copia firmada: {integridad.copia_firmada ? (integridad.copia_firmada.coincide ? 'archivo íntegro' : 'archivo faltante o modificado') : 'aún no registrada'}.</span>
      </div>}
      <h4>Historial de estados</h4>
      {eventos.length === 0 && <p className="movimiento-note">Todavía no hay cambios de estado.</p>}
      {eventos.map((item) => <article className="movimiento-entry" key={item.id}>
        <strong>{stateLabels[item.estado_anterior] || item.estado_anterior} → {stateLabels[item.estado_nuevo] || item.estado_nuevo}</strong>
        <span>{new Date(item.fecha).toLocaleString('es-CL')} · {item.usuario_nombre || `Usuario #${item.usuario_id}`}</span>
        {item.motivo && <span>Motivo: {item.motivo}</span>}
        {item.hash_copia_firmada && <span>Huella SHA-256 de la copia: {item.hash_copia_firmada}</span>}
      </article>)}
    </details>
  </MovimientoShell>;
}
