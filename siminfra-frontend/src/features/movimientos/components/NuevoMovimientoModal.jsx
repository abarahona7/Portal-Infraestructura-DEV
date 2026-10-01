import { useEffect, useState } from 'react';
import apiClient from '../../../api/client';
import { createMovimiento, downloadActa, movimientoError } from '../../../api/movimientosApi';
import MovimientoShell from './MovimientoShell';

const TYPES = [
  ['ASIGNACION', 'Asignación'],
  ['PRESTAMO', 'Préstamo'],
  ['DEVOLUCION', 'Devolución'],
  ['REASIGNACION', 'Reasignación'],
  ['CAMBIO', 'Cambio de equipo'],
  ['INGRESO_REPARACION', 'Ingreso a reparación'],
  ['SALIDA_REPARACION', 'Salida de reparación'],
  ['BAJA', 'Baja'],
];
const labels = Object.fromEntries(TYPES);
const initial = {
  tipo_movimiento: 'ASIGNACION', activo_id: '', colaborador_destino_id: '',
  ubicacion_destino: '', estado_fisico: 'USADO', estado_operativo_resultante: 'STOCK',
  accesorios_detalle: [], observaciones: '',
};

const receivesAsset = (kind) => ['ASIGNACION', 'PRESTAMO', 'REASIGNACION'].includes(kind);
const needsOrigin = (kind, asset) => ['DEVOLUCION', 'REASIGNACION'].includes(kind)
  || (kind === 'INGRESO_REPARACION' && Boolean(asset?.usuario));
const usesChecklist = (kind, asset) => ['ASIGNACION', 'PRESTAMO', 'DEVOLUCION', 'REASIGNACION'].includes(kind)
  || (kind === 'INGRESO_REPARACION' && Boolean(asset?.usuario));
const canMove = (kind, asset) => {
  if (!asset) return false;
  const assigned = Boolean(asset.usuario);
  if (['ASIGNACION', 'PRESTAMO', 'BAJA'].includes(kind)) return !assigned && asset.estado === 'STOCK';
  if (kind === 'DEVOLUCION') return assigned && ['ASIGNADO', 'PRESTAMO', 'MANTENCION'].includes(asset.estado);
  if (kind === 'REASIGNACION') return assigned && ['ASIGNADO', 'PRESTAMO'].includes(asset.estado);
  if (kind === 'INGRESO_REPARACION') return assigned
    ? ['ASIGNADO', 'PRESTAMO'].includes(asset.estado) : asset.estado === 'STOCK';
  if (kind === 'SALIDA_REPARACION') return !assigned && asset.estado === 'MANTENCION';
  return false;
};
const resultingState = (kind, returnState) => ({
  ASIGNACION: 'ASIGNADO', PRESTAMO: 'PRESTAMO', DEVOLUCION: returnState, REASIGNACION: 'ASIGNADO',
  INGRESO_REPARACION: 'MANTENCION', SALIDA_REPARACION: 'STOCK', BAJA: 'BAJA',
})[kind];

export default function NuevoMovimientoModal({ open, onClose, onCompleted, onChangeEquipment }) {
  const [form, setForm] = useState(initial);
  const [assetSearch, setAssetSearch] = useState('');
  const [personSearch, setPersonSearch] = useState('');
  const [assets, setAssets] = useState([]);
  const [people, setPeople] = useState([]);
  const [selectedPerson, setSelectedPerson] = useState(null);
  const [asset, setAsset] = useState(null);
  const [preview, setPreview] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (!open) return undefined;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      apiClient.get('/equipos/', { params: { search: assetSearch, page_size: 30 }, signal: controller.signal })
        .then(({ data }) => setAssets(data.results || []))
        .catch((err) => { if (err.code !== 'ERR_CANCELED') setError(movimientoError(err)); });
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [assetSearch, open, result]);

  useEffect(() => {
    if (!open || !receivesAsset(form.tipo_movimiento)) return undefined;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      apiClient.get('/usuarios/', { params: { search: personSearch, estado: 'ACTIVO', page_size: 30 }, signal: controller.signal })
        .then(({ data }) => setPeople(data.results || []))
        .catch((err) => { if (err.code !== 'ERR_CANCELED') setError(movimientoError(err)); });
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [personSearch, open, form.tipo_movimiento]);

  if (!open) return null;
  const kind = form.tipo_movimiento;
  const needsDestination = receivesAsset(kind);
  const fromCustodian = needsOrigin(kind, asset);
  const checklist = usesChecklist(kind, asset);
  const canUseAsset = canMove(kind, asset);
  const setField = (name, value) => {
    setForm((current) => ({ ...current, [name]: value }));
    setPreview(false);
    setError('');
  };
  const setSelectedAsset = (id) => {
    const selected = assets.find((item) => Number(item.id) === Number(id)) || null;
    setAsset(selected);
    setSelectedPerson(null);
    setForm((current) => ({
      ...current, activo_id: id, colaborador_destino_id: '',
      ubicacion_destino: selected?.ubicacion_actual || '',
      estado_fisico: selected?.estado_fisico || 'USADO',
      accesorios_detalle: (selected?.accesorios_requeridos || []).map((name) => ({ nombre: name, entregado: true, nota: '' })),
    }));
    setPreview(false);
    setError('');
  };
  const close = () => {
    if (busy) return;
    setForm(initial); setAsset(null); setSelectedPerson(null);
    setAssetSearch(''); setPersonSearch(''); setPreview(false); setResult(null); setError('');
    onClose();
  };
  const setType = (type) => {
    if (type === 'CAMBIO') {
      close();
      onChangeEquipment();
      return;
    }
    setForm({ ...initial, tipo_movimiento: type });
    setAsset(null); setSelectedPerson(null); setPreview(false); setResult(null); setError('');
  };
  const validate = () => {
    if (!asset) return 'Seleccione un activo.';
    if (!canUseAsset) return 'El estado actual del activo no permite este movimiento.';
    if (needsDestination && !form.colaborador_destino_id) return 'Seleccione el colaborador que recibe el activo.';
    if (needsDestination && Number(form.colaborador_destino_id) === Number(asset.usuario)) return 'Seleccione un colaborador distinto del custodio actual.';
    if (needsDestination && !selectedPerson?.rut) return 'El colaborador necesita un RUT válido antes de registrar el movimiento.';
    if (!form.ubicacion_destino.trim()) return 'Indique la ubicación de destino.';
    if ((form.estado_fisico === 'DANADO' || ['INGRESO_REPARACION', 'SALIDA_REPARACION', 'BAJA'].includes(kind)) && !form.observaciones.trim()) return 'Indique el motivo o trabajo realizado.';
    if (checklist && form.accesorios_detalle.some((item) => !item.entregado && !item.nota?.trim())) return 'Explique cada accesorio faltante.';
    return '';
  };
  const confirmPreview = () => {
    const issue = validate();
    if (issue) { setError(issue); return; }
    setPreview(true); setError('');
  };
  const submit = async () => {
    const issue = validate();
    if (issue) { setError(issue); setPreview(false); return; }
    setBusy(true); setError('');
    try {
      const payload = {
        tipo_movimiento: kind, activo_id: Number(form.activo_id),
        ubicacion_destino: form.ubicacion_destino.trim(), estado_fisico: form.estado_fisico,
        accesorios_detalle: checklist ? form.accesorios_detalle.map((item) => ({
          ...item, nombre: item.nombre.trim(), nota: item.nota?.trim() || '',
        })) : [],
        observaciones: form.observaciones.trim(),
        ...(kind === 'DEVOLUCION' ? { estado_operativo_resultante: form.estado_operativo_resultante } : {}),
        ...(fromCustodian ? { colaborador_origen_id: asset.usuario } : {}),
        ...(needsDestination ? { colaborador_destino_id: Number(form.colaborador_destino_id) } : {}),
      };
      const created = await createMovimiento(payload);
      setResult(created);
      onCompleted?.();
    } catch (err) { setError(movimientoError(err)); setPreview(false); }
    finally { setBusy(false); }
  };
  const setAccessory = (index, patch) => setForm((current) => ({ ...current,
    accesorios_detalle: current.accesorios_detalle.map((entry, i) => i === index ? { ...entry, ...patch } : entry),
  }));
  const addAccessory = () => setForm((current) => ({ ...current,
    accesorios_detalle: [...current.accesorios_detalle, { nombre: '', entregado: true, nota: '' }],
  }));

  return <MovimientoShell title="Nuevo movimiento de activo" onClose={close} busy={busy} footer={
    result ? <><button className="movimiento-button" type="button" onClick={close}>Cerrar</button><button className="movimiento-button movimiento-button-primary" type="button" onClick={() => downloadActa(result.acta).catch((err) => setError(movimientoError(err)))}>Descargar comprobante</button></>
      : <><button className="movimiento-button" type="button" onClick={preview ? () => setPreview(false) : close} disabled={busy}>{preview ? 'Volver' : 'Cancelar'}</button><button className="movimiento-button movimiento-button-primary" type="button" disabled={busy} onClick={preview ? submit : confirmPreview}>{preview ? 'Confirmar movimiento' : 'Vista previa'}</button></>
  }>
    {error && <p role="alert" className="movimiento-error">{error}</p>}
    {result ? <div className="movimiento-success"><strong>Movimiento registrado.</strong><p>Comprobante {result.acta.folio} generado y guardado.</p></div>
      : preview ? <dl className="movimiento-summary">
        <dt>Movimiento</dt><dd>{labels[kind]}</dd>
        <dt>Activo</dt><dd>{asset?.tipo} {asset?.marca} {asset?.modelo} · Serie {asset?.numero_serie || 'N/I'}</dd>
        {fromCustodian && <><dt>Custodio origen</dt><dd>{asset?.usuario_nombre}</dd></>}
        {needsDestination && <><dt>Colaborador destino</dt><dd>{selectedPerson?.nombre_completo}</dd></>}
        <dt>Ubicación destino</dt><dd>{form.ubicacion_destino}</dd>
        <dt>Estado resultante</dt><dd>{resultingState(kind, form.estado_operativo_resultante)}</dd>
        <dt>Estado físico</dt><dd>{form.estado_fisico}</dd>
        {checklist && <><dt>Accesorios</dt><dd>{form.accesorios_detalle.map((a) => `${a.nombre}: ${a.entregado ? 'entregado' : `faltante (${a.nota})`}`).join(', ') || 'Sin accesorios'}</dd></>}
        <dt>Observaciones</dt><dd>{form.observaciones || 'Sin observaciones'}</dd>
      </dl>
        : <div className="movimiento-fields">
          <label>Tipo de movimiento<select value={kind} onChange={(event) => setType(event.target.value)}>{TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label>Buscar activo<input value={assetSearch} onChange={(event) => setAssetSearch(event.target.value)} placeholder="Serie, activo fijo, marca o modelo" /></label>
          <label>Activo<select value={form.activo_id} onChange={(event) => setSelectedAsset(event.target.value)}><option value="">Seleccione...</option>{assets.map((item) => <option key={item.id} value={item.id}>{item.tipo} {item.marca} {item.modelo} · {item.numero_serie || item.af || `ID ${item.id}`} · {item.estado}</option>)}</select></label>
          {asset && !canUseAsset && <p className="movimiento-error">El activo está {asset.estado}. Seleccione otro o registre el movimiento previo.</p>}
          {fromCustodian && <p className="movimiento-note">Custodio actual: {asset?.usuario_nombre || 'Sin registro'}</p>}
          {needsDestination && <><label>Buscar colaborador<input value={personSearch} onChange={(event) => setPersonSearch(event.target.value)} placeholder="Nombre, usuario de red o correo" /></label><label>Colaborador destino<select value={form.colaborador_destino_id} onChange={(event) => { setField('colaborador_destino_id', event.target.value); setSelectedPerson(people.find((person) => String(person.id) === event.target.value) || null); }}><option value="">Seleccione...</option>{people.map((person) => <option key={person.id} value={person.id}>{person.nombre_completo} ({person.usuario_red})</option>)}</select></label></>}
          <label>Ubicación destino<input value={form.ubicacion_destino} maxLength={100} onChange={(event) => setField('ubicacion_destino', event.target.value)} /></label>
          <label>Estado físico<select value={form.estado_fisico} onChange={(event) => setField('estado_fisico', event.target.value)}><option value="NUEVO">Nuevo</option><option value="SEMINUEVO">Seminuevo</option><option value="USADO">Usado</option><option value="DANADO">Dañado</option></select></label>
          {kind === 'DEVOLUCION' && <label>Destino operativo<select value={form.estado_operativo_resultante} onChange={(event) => setField('estado_operativo_resultante', event.target.value)}><option value="STOCK">Disponible</option><option value="MANTENCION">En reparación</option></select></label>}
          {checklist && <fieldset style={{ gridColumn: '1 / -1' }}><legend>Accesorios {needsDestination ? 'entregados' : 'recibidos'}</legend>{form.accesorios_detalle.map((entry, index) => <div className="movimiento-accessory" key={index}><label><input type="checkbox" checked={entry.entregado} onChange={(event) => setAccessory(index, { entregado: event.target.checked })} />{needsDestination ? 'Entregado' : entry.nombre}</label>{needsDestination && <input value={entry.nombre} maxLength={100} aria-label={`Nombre accesorio ${index + 1}`} onChange={(event) => setAccessory(index, { nombre: event.target.value })} />}{!entry.entregado && <input value={entry.nota || ''} maxLength={200} placeholder="Motivo del faltante" aria-label={`Nota accesorio ${index + 1}`} onChange={(event) => setAccessory(index, { nota: event.target.value })} />}</div>)}{needsDestination && <button type="button" className="movimiento-button movimiento-add" onClick={addAccessory}>Agregar accesorio</button>}</fieldset>}
          <label style={{ gridColumn: '1 / -1' }}>Observaciones<textarea rows={3} maxLength={2000} value={form.observaciones} onChange={(event) => setField('observaciones', event.target.value)} /></label>
        </div>}
  </MovimientoShell>;
}
