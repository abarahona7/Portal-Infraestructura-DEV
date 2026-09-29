import { useEffect, useState } from 'react';
import apiClient from '../../../api/client';
import { createMovimiento, downloadActa, movimientoError } from '../../../api/movimientosApi';
import MovimientoShell from './MovimientoShell';

const initial = {
  tipo_movimiento: 'ASIGNACION', activo_id: '', colaborador_destino_id: '',
  ubicacion_destino: '', estado_fisico: 'USADO', accesorios_detalle: [], observaciones: '',
};

export default function NuevoMovimientoModal({ open, onClose, onCompleted }) {
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
    if (!open || form.tipo_movimiento !== 'ASIGNACION') return undefined;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      apiClient.get('/usuarios/', { params: { search: personSearch, estado: 'ACTIVO', page_size: 30 }, signal: controller.signal })
        .then(({ data }) => setPeople(data.results || []))
        .catch((err) => { if (err.code !== 'ERR_CANCELED') setError(movimientoError(err)); });
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [personSearch, open, form.tipo_movimiento]);

  if (!open) return null;
  const setField = (name, value) => { setForm((current) => ({ ...current, [name]: value })); setPreview(false); setError(''); };
  const setSelectedAsset = (id) => {
    const selected = assets.find((item) => Number(item.id) === Number(id)) || null;
    setAsset(selected);
    setForm((current) => ({ ...current, activo_id: id,
      colaborador_destino_id: '',
      ubicacion_destino: selected?.ubicacion_actual || '',
      estado_fisico: selected?.estado_fisico || 'USADO',
      accesorios_detalle: (selected?.accesorios_requeridos || []).map((name) => ({ nombre: name, entregado: true, nota: '' })),
    }));
    setPreview(false); setError('');
  };
  const setType = (type) => {
    setForm({ ...initial, tipo_movimiento: type }); setAsset(null); setSelectedPerson(null); setPreview(false); setResult(null); setError('');
  };
  const close = () => { if (busy) return; setForm(initial); setAsset(null); setSelectedPerson(null); setAssetSearch(''); setPersonSearch(''); setPreview(false); setResult(null); setError(''); onClose(); };
  const isReturn = form.tipo_movimiento === 'DEVOLUCION';
  const canUseAsset = asset && (isReturn ? asset.usuario && ['ASIGNADO', 'PRESTAMO', 'MANTENCION'].includes(asset.estado) : !asset.usuario && asset.estado === 'STOCK');
  const validate = () => {
    if (!asset) return 'Seleccione un activo.';
    if (!canUseAsset) return 'El estado actual del activo no permite este movimiento.';
    if (!isReturn && !form.colaborador_destino_id) return 'Seleccione el colaborador que recibe el activo.';
    if (!isReturn && !selectedPerson?.rut) return 'El colaborador necesita un RUT válido en su ficha antes de generar un acta.';
    if (!form.ubicacion_destino.trim()) return 'Indique la ubicación de destino.';
    if (form.estado_fisico === 'DANADO' && !form.observaciones.trim()) return 'Describa el daño del activo.';
    if (form.accesorios_detalle.some((item) => !item.entregado && !item.nota?.trim())) return 'Explique cada accesorio faltante.';
    return '';
  };
  const confirmPreview = () => {
    const issue = validate(); if (issue) { setError(issue); return; }
    setPreview(true); setError('');
  };
  const submit = async () => {
    const issue = validate(); if (issue) { setError(issue); setPreview(false); return; }
    setBusy(true); setError('');
    try {
      const payload = { tipo_movimiento: form.tipo_movimiento, activo_id: Number(form.activo_id),
        ubicacion_destino: form.ubicacion_destino.trim(), estado_fisico: form.estado_fisico,
        accesorios_detalle: form.accesorios_detalle.map((item) => ({ ...item, nombre: item.nombre.trim(), nota: item.nota?.trim() || '' })),
        observaciones: form.observaciones.trim(),
        ...(isReturn ? { colaborador_origen_id: asset.usuario } : { colaborador_destino_id: Number(form.colaborador_destino_id) }),
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
  return (
    <MovimientoShell title="Nuevo movimiento de activo" onClose={close} busy={busy} footer={
      result ? <><button className="movimiento-button" type="button" onClick={close}>Cerrar</button><button className="movimiento-button movimiento-button-primary" type="button" onClick={() => downloadActa(result.acta).catch((err) => setError(movimientoError(err)))}>Descargar acta {result.acta.folio}</button></>
        : <><button className="movimiento-button" type="button" onClick={preview ? () => setPreview(false) : close} disabled={busy}>{preview ? 'Volver' : 'Cancelar'}</button><button className="movimiento-button movimiento-button-primary" type="button" disabled={busy} onClick={preview ? submit : confirmPreview}>{preview ? 'Confirmar y generar acta' : 'Vista previa'}</button></>
    }>
      {error && <p role="alert" className="movimiento-error">{error}</p>}
      {result ? <div className="movimiento-success"><strong>Movimiento registrado.</strong><p>Acta {result.acta.folio} generada y guardada.</p></div>
        : preview ? <dl className="movimiento-summary"><dt>Movimiento</dt><dd>{form.tipo_movimiento}</dd><dt>Activo</dt><dd>{asset?.tipo} {asset?.marca} {asset?.modelo} · Serie {asset?.numero_serie || 'N/I'}</dd><dt>Colaborador</dt><dd>{isReturn ? asset?.usuario_nombre : selectedPerson?.nombre_completo}</dd><dt>Ubicación destino</dt><dd>{form.ubicacion_destino}</dd><dt>Estado físico</dt><dd>{form.estado_fisico}</dd><dt>Accesorios</dt><dd>{form.accesorios_detalle.map((a) => `${a.nombre}: ${a.entregado ? 'entregado' : `faltante (${a.nota})`}`).join(', ') || 'Sin accesorios'}</dd><dt>Observaciones</dt><dd>{form.observaciones || 'Sin observaciones'}</dd></dl>
          : <div className="movimiento-fields">
            <label>Tipo de movimiento<select value={form.tipo_movimiento} onChange={(e) => setType(e.target.value)}><option value="ASIGNACION">Asignación</option><option value="DEVOLUCION">Devolución</option></select></label>
            <label>Buscar activo<input value={assetSearch} onChange={(e) => setAssetSearch(e.target.value)} placeholder="Serie, activo fijo, marca o modelo" /></label>
            <label>Activo<select value={form.activo_id} onChange={(e) => setSelectedAsset(e.target.value)}><option value="">Seleccione...</option>{assets.map((item) => <option key={item.id} value={item.id}>{item.tipo} {item.marca} {item.modelo} · {item.numero_serie || item.af || `ID ${item.id}`} · {item.estado}</option>)}</select></label>
            {asset && !canUseAsset && <p className="movimiento-error">El activo está {asset.estado}. Seleccione otro o registre el movimiento válido.</p>}
            {isReturn ? <p className="movimiento-note">Devuelve: {asset?.usuario_nombre || 'Seleccione un activo asignado'}</p> : <><label>Buscar colaborador<input value={personSearch} onChange={(e) => setPersonSearch(e.target.value)} placeholder="Nombre, usuario de red o correo" /></label><label>Colaborador destino<select value={form.colaborador_destino_id} onChange={(e) => { setField('colaborador_destino_id', e.target.value); setSelectedPerson(people.find((person) => String(person.id) === e.target.value) || null); }}><option value="">Seleccione...</option>{people.map((person) => <option key={person.id} value={person.id}>{person.nombre_completo} ({person.usuario_red})</option>)}</select></label></>}
            <label>Ubicación destino<input value={form.ubicacion_destino} maxLength={100} onChange={(e) => setField('ubicacion_destino', e.target.value)} /></label>
            <label>Estado físico<select value={form.estado_fisico} onChange={(e) => setField('estado_fisico', e.target.value)}><option value="NUEVO">Nuevo</option><option value="SEMINUEVO">Seminuevo</option><option value="USADO">Usado</option><option value="DANADO">Dañado</option></select></label>
            <fieldset style={{ gridColumn: '1 / -1' }}><legend>Accesorios {isReturn ? 'devueltos' : 'entregados'}</legend>{form.accesorios_detalle.map((entry, index) => <div className="movimiento-accessory" key={index}><label><input type="checkbox" checked={entry.entregado} onChange={(e) => setAccessory(index, { entregado: e.target.checked })} />{isReturn ? entry.nombre : 'Entregado'}</label>{!isReturn && <input value={entry.nombre} maxLength={100} aria-label={`Nombre accesorio ${index + 1}`} onChange={(e) => setAccessory(index, { nombre: e.target.value })} />}{!entry.entregado && <input value={entry.nota || ''} maxLength={200} placeholder="Motivo del faltante" aria-label={`Nota accesorio ${index + 1}`} onChange={(e) => setAccessory(index, { nota: e.target.value })} />}</div>)}{!isReturn && <button type="button" className="movimiento-button movimiento-add" onClick={addAccessory}>Agregar accesorio</button>}</fieldset>
            <label style={{ gridColumn: '1 / -1' }}>Observaciones<textarea rows={3} maxLength={2000} value={form.observaciones} onChange={(e) => setField('observaciones', e.target.value)} /></label>
          </div>}
    </MovimientoShell>
  );
}
