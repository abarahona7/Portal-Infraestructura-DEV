import { useEffect, useState } from 'react';
import apiClient from '../../../api/client';
import { downloadActa, movimientoError } from '../../../api/movimientosApi';
import MovimientoShell from './MovimientoShell';

const initial = {
  estado_fisico_origen: 'USADO', estado_fisico_destino: 'USADO',
  estado_operativo_origen: 'STOCK', accesorios_devueltos: [],
  accesorios_entregados: [], observaciones: '',
};
const physicalOptions = [['NUEVO', 'Nuevo'], ['SEMINUEVO', 'Seminuevo'], ['USADO', 'Usado'], ['DANADO', 'Dañado']];
const assetLabel = (asset) => `${asset.tipo} ${asset.marca} ${asset.modelo} · ${asset.numero_serie || asset.af || `ID ${asset.id}`}`;

function Checklist({ title, items, editable, verb = 'Entregado', onChange, onAdd }) {
  return <fieldset style={{ gridColumn: '1 / -1' }}>
    <legend>{title}</legend>
    {items.map((item, index) => <div className="movimiento-accessory" key={index}>
      <label><input type="checkbox" checked={item.entregado} onChange={(event) => onChange(index, { entregado: event.target.checked })} />{editable ? verb : item.nombre}</label>
      {editable && <input value={item.nombre} maxLength={100} aria-label={`Nombre accesorio ${index + 1}`} onChange={(event) => onChange(index, { nombre: event.target.value })} />}
      {!item.entregado && <input value={item.nota || ''} maxLength={200} placeholder="Motivo del faltante" aria-label={`Nota accesorio ${index + 1}`} onChange={(event) => onChange(index, { nota: event.target.value })} />}
    </div>)}
    {editable && <button type="button" className="movimiento-button movimiento-add" disabled={items.length >= 20} onClick={onAdd}>Agregar accesorio</button>}
  </fieldset>;
}

export default function CambioEquipoModal({ open, onClose, onCompleted }) {
  const [oldSearch, setOldSearch] = useState('');
  const [newSearch, setNewSearch] = useState('');
  const [oldOptions, setOldOptions] = useState([]);
  const [newOptions, setNewOptions] = useState([]);
  const [oldAsset, setOldAsset] = useState(null);
  const [newAsset, setNewAsset] = useState(null);
  const [form, setForm] = useState(initial);
  const [preview, setPreview] = useState(false);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return undefined;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      apiClient.get('/equipos/', { params: { search: oldSearch, page_size: 30 }, signal: controller.signal })
        .then(({ data }) => setOldOptions(data.results || []))
        .catch((err) => { if (err.code !== 'ERR_CANCELED') setError(movimientoError(err)); });
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [oldSearch, open]);
  useEffect(() => {
    if (!open) return undefined;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      apiClient.get('/equipos/', { params: { search: newSearch, page_size: 30 }, signal: controller.signal })
        .then(({ data }) => setNewOptions(data.results || []))
        .catch((err) => { if (err.code !== 'ERR_CANCELED') setError(movimientoError(err)); });
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [newSearch, open]);

  if (!open) return null;
  const setField = (field, value) => { setForm((current) => ({ ...current, [field]: value })); setPreview(false); setError(''); };
  const selectOld = (id) => {
    const selected = oldOptions.find((item) => String(item.id) === id) || null;
    setOldAsset(selected);
    setForm((current) => ({ ...current,
      estado_fisico_origen: selected?.estado_fisico || 'USADO',
      accesorios_devueltos: (selected?.accesorios_requeridos || []).map((name) => ({ nombre: name, entregado: true, nota: '' })),
    }));
    setPreview(false); setError('');
  };
  const selectNew = (id) => {
    const selected = newOptions.find((item) => String(item.id) === id) || null;
    setNewAsset(selected);
    setForm((current) => ({ ...current,
      estado_fisico_destino: selected?.estado_fisico || 'USADO',
      accesorios_entregados: (selected?.accesorios_requeridos || []).map((name) => ({ nombre: name, entregado: true, nota: '' })),
    }));
    setPreview(false); setError('');
  };
  const updateAccessory = (field, index, patch) => setForm((current) => ({ ...current,
    [field]: current[field].map((entry, i) => i === index ? { ...entry, ...patch } : entry),
  }));
  const validate = () => {
    if (!oldAsset || !newAsset) return 'Seleccione los dos equipos.';
    if (oldAsset.id === newAsset.id) return 'El equipo de reemplazo debe ser distinto.';
    if (!oldAsset.usuario || !['ASIGNADO', 'PRESTAMO'].includes(oldAsset.estado)) return 'El equipo anterior debe estar asignado o en préstamo.';
    if (newAsset.usuario || newAsset.estado !== 'STOCK') return 'El equipo nuevo debe estar disponible.';
    if (!form.observaciones.trim()) return 'Explique el motivo del cambio de equipo.';
    if ([...form.accesorios_devueltos, ...form.accesorios_entregados].some((item) => !item.nombre.trim())) return 'Indique el nombre de cada accesorio.';
    if ([...form.accesorios_devueltos, ...form.accesorios_entregados].some((item) => !item.entregado && !item.nota?.trim())) return 'Explique cada accesorio faltante.';
    return '';
  };
  const close = () => {
    if (busy) return;
    setOldSearch(''); setNewSearch(''); setOldAsset(null); setNewAsset(null);
    setForm(initial); setPreview(false); setResult(null); setError('');
    onClose();
  };
  const submit = async () => {
    const issue = validate();
    if (issue) { setError(issue); setPreview(false); return; }
    setBusy(true); setError('');
    try {
      const { data } = await apiClient.post('/movimientos/cambio/', {
        activo_origen_id: oldAsset.id, activo_destino_id: newAsset.id,
        colaborador_id: oldAsset.usuario,
        estado_fisico_origen: form.estado_fisico_origen,
        estado_fisico_destino: form.estado_fisico_destino,
        estado_operativo_origen: form.estado_operativo_origen,
        accesorios_devueltos: form.accesorios_devueltos.map((item) => ({ ...item, nombre: item.nombre.trim(), nota: item.nota?.trim() || '' })),
        accesorios_entregados: form.accesorios_entregados.map((item) => ({ ...item, nombre: item.nombre.trim(), nota: item.nota?.trim() || '' })),
        observaciones: form.observaciones.trim(),
      });
      setResult(data);
      onCompleted?.();
    } catch (err) { setError(movimientoError(err)); setPreview(false); }
    finally { setBusy(false); }
  };
  const confirmPreview = () => {
    const issue = validate();
    if (issue) { setError(issue); return; }
    setPreview(true); setError('');
  };

  return <MovimientoShell title="Cambio de equipo" onClose={close} busy={busy} footer={
    result ? <><button type="button" className="movimiento-button" onClick={close}>Cerrar</button><button type="button" className="movimiento-button" onClick={() => downloadActa(result.salida.acta).catch((err) => setError(movimientoError(err)))}>Descargar comprobante de devolución</button><button type="button" className="movimiento-button movimiento-button-primary" onClick={() => downloadActa(result.entrada.acta).catch((err) => setError(movimientoError(err)))}>Descargar comprobante de entrega</button></>
      : <><button type="button" className="movimiento-button" disabled={busy} onClick={preview ? () => setPreview(false) : close}>{preview ? 'Volver' : 'Cancelar'}</button><button type="button" className="movimiento-button movimiento-button-primary" disabled={busy} onClick={preview ? submit : confirmPreview}>{preview ? 'Confirmar ambos movimientos' : 'Vista previa'}</button></>
  }>
    {!result && <p className="movimiento-note">Usa esta opción cuando una persona entrega un equipo y recibe otro. Se registran ambas acciones juntas.</p>}
    {error && <p className="movimiento-error" role="alert">{error}</p>}
    {result ? <div className="movimiento-success"><strong>Cambio registrado.</strong><p>Se guardaron dos comprobantes vinculados: {result.salida.acta.folio} y {result.entrada.acta.folio}.</p></div>
      : preview ? <dl className="movimiento-summary">
        <dt>Colaborador</dt><dd>{oldAsset?.usuario_nombre}</dd>
        <dt>Equipo devuelto</dt><dd>{assetLabel(oldAsset)} → {form.estado_operativo_origen}</dd>
        <dt>Equipo entregado</dt><dd>{assetLabel(newAsset)} → ASIGNADO</dd>
        <dt>Accesorios devueltos</dt><dd>{form.accesorios_devueltos.map((item) => `${item.nombre}: ${item.entregado ? 'recibido' : 'faltante'}`).join(', ') || 'Sin accesorios'}</dd>
        <dt>Accesorios entregados</dt><dd>{form.accesorios_entregados.map((item) => `${item.nombre}: ${item.entregado ? 'entregado' : 'faltante'}`).join(', ') || 'Sin accesorios'}</dd>
        <dt>Motivo</dt><dd>{form.observaciones}</dd>
        <dt>Documentos</dt><dd>Se guardarán dos comprobantes vinculados al cambio de equipo.</dd>
      </dl>
        : <div className="movimiento-fields">
          <label>Buscar equipo anterior<input value={oldSearch} onChange={(event) => setOldSearch(event.target.value)} placeholder="Serie, activo fijo, marca o modelo" /></label>
          <label>Equipo anterior<select value={oldAsset?.id || ''} onChange={(event) => selectOld(event.target.value)}><option value="">Seleccione...</option>{oldOptions.map((item) => <option value={item.id} key={item.id}>{assetLabel(item)} · {item.estado}</option>)}</select></label>
          {oldAsset && <p className="movimiento-note">Custodio: {oldAsset.usuario_nombre || 'Sin asignar'} · Estado: {oldAsset.estado}</p>}
          <label>Buscar reemplazo<input value={newSearch} onChange={(event) => setNewSearch(event.target.value)} placeholder="Serie, activo fijo, marca o modelo" /></label>
          <label>Equipo de reemplazo<select value={newAsset?.id || ''} onChange={(event) => selectNew(event.target.value)}><option value="">Seleccione...</option>{newOptions.map((item) => <option value={item.id} key={item.id}>{assetLabel(item)} · {item.estado}</option>)}</select></label>
          <label>Estado del equipo anterior<select value={form.estado_fisico_origen} onChange={(event) => setField('estado_fisico_origen', event.target.value)}>{physicalOptions.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
          <label>Estado del reemplazo<select value={form.estado_fisico_destino} onChange={(event) => setField('estado_fisico_destino', event.target.value)}>{physicalOptions.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
          <label>Destino del equipo anterior<select value={form.estado_operativo_origen} onChange={(event) => setField('estado_operativo_origen', event.target.value)}><option value="STOCK">Disponible</option><option value="MANTENCION">En reparación</option></select></label>
          <Checklist title="Accesorios recibidos del equipo anterior" items={form.accesorios_devueltos} editable verb="Recibido" onChange={(index, patch) => updateAccessory('accesorios_devueltos', index, patch)} onAdd={() => setForm((current) => ({ ...current, accesorios_devueltos: [...current.accesorios_devueltos, { nombre: '', entregado: true, nota: '' }] }))} />
          <Checklist title="Accesorios entregados con el reemplazo" items={form.accesorios_entregados} editable onChange={(index, patch) => updateAccessory('accesorios_entregados', index, patch)} onAdd={() => setForm((current) => ({ ...current, accesorios_entregados: [...current.accesorios_entregados, { nombre: '', entregado: true, nota: '' }] }))} />
          <label style={{ gridColumn: '1 / -1' }}>Motivo y observaciones<textarea rows={3} maxLength={2000} value={form.observaciones} onChange={(event) => setField('observaciones', event.target.value)} /></label>
        </div>}
  </MovimientoShell>;
}
