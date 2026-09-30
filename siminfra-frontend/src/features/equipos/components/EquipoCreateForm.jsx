import {
  equipmentUsesHostname,
  equipmentUsesMobileLine,
  normalizeEquipmentFieldsByType,
} from '../../../utils/equipmentHelpers';

export default function EquipoCreateForm({
  equipo,
  onChange,
  formatEquipmentType,
  onHostnameChange,
}) {
  const updateField = (field, value) => {
    onChange({
      ...equipo,
      [field]: value,
    });
  };

  const inputStyle = {
    width: '100%',
    padding: '0.6rem',
    borderRadius: '6px',
    border: '1px solid #cbd5e1',
    marginTop: '4px',
    boxSizing: 'border-box',
  };

  const labelStyle = {
    fontSize: '0.8rem',
    color: '#64748b',
    fontWeight: 'bold',
  };

  const tipoActual = formatEquipmentType(
    equipo.tipo
  );

  const usaHostname =
    equipmentUsesHostname(tipoActual);

  const usaLineaMovil =
    equipmentUsesMobileLine(tipoActual);

  const esCelular =
    tipoActual === 'Celular';

  const esMac =
    tipoActual === 'Mac';


  const handleTipoChange = (nuevoTipo) => {
    const nuevoEstado =
      normalizeEquipmentFieldsByType(
        equipo,
        nuevoTipo
      );

    onChange(nuevoEstado);
  };

  return (
    <>
      {/* =========================
          TIPO
      ========================= */}

      <div>
        <label style={labelStyle}>
          Tipo de Equipo *
        </label>

        <select
          aria-label="Tipo de equipo"
          value={tipoActual}
          onChange={(e) =>
            handleTipoChange(e.target.value)
          }
          style={inputStyle}
        >
          <optgroup label="Equipos principales">
            <option value="Notebook">
              Notebook
            </option>

            <option value="Celular">
              Celular
            </option>

            <option value="Tablet">
              Tablet
            </option>

            <option value="Mac">
              Mac
            </option>

            <option value="BAM / Router">
              BAM / Router
            </option>
          </optgroup>

          <optgroup label="Periféricos">
            <option value="Monitor">
              Monitor
            </option>

            <option value="Adaptador">
              Adaptador
            </option>

            <option value="Audífonos">
              Audífonos
            </option>

            <option value="Teclado">
              Teclado
            </option>

            <option value="Mouse">
              Mouse
            </option>

            <option value="Docking">
              Docking
            </option>

            <option value="Otro Periférico">
              Otro Periférico
            </option>
          </optgroup>
        </select>
      </div>

      {/* =========================
          MARCA
      ========================= */}

      <div>
        <label style={labelStyle}>
          Marca *
        </label>

        <input
          aria-label="Marca"
          type="text"
          required
          value={equipo.marca || ''}
          maxLength={50}
          onChange={(e) =>
            updateField(
              'marca',
              e.target.value
            )
          }
          style={inputStyle}
        />
      </div>

      {/* =========================
          MODELO
      ========================= */}

      <div>
        <label style={labelStyle}>
          Modelo *
        </label>

        <input
          aria-label="Modelo"
          type="text"
          required
          value={equipo.modelo || ''}
          maxLength={50}
          onChange={(e) =>
            updateField(
              'modelo',
              e.target.value
            )
          }
          style={inputStyle}
        />
      </div>

      {/* =========================
          NÚMERO DE SERIE
      ========================= */}

      <div>
        <label style={labelStyle}>
          N° de Serie
        </label>

        <input
          aria-label="Número de serie"
          type="text"
          maxLength={20}
          value={
            equipo.numero_serie || ''
          }
          onChange={(e) =>
            updateField(
              'numero_serie',
              e.target.value.slice(0, 20)
            )
          }
          placeholder="Máx. 20 caracteres"
          style={inputStyle}
        />
      </div>

      {/* =========================
          CELULAR
      ========================= */}

      {esCelular && (
        <div
          style={{
            backgroundColor: '#f0fdf4',
            padding: '0.8rem',
            borderRadius: '8px',
            border: '1px solid #bbf7d0',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
          }}
        >
          <span
            style={{
              fontSize: '0.75rem',
              fontWeight: 'bold',
              color: '#166534',
              textTransform: 'uppercase',
            }}
          >
            Detalles de Celular
          </span>

          {/* SIM */}

          <div>
            <label
              style={{
                ...labelStyle,
                color: '#166534',
              }}
            >
              SIM / N° Celular
            </label>

            <input
              aria-label="Número de teléfono"
              type="text"
              inputMode="tel"
              maxLength={12}
              value={
                equipo.numero_telefono || ''
              }
              onChange={(e) => {
                let value = e.target.value;

                // Solo números y +
                value = value.replace(/[^\d+]/g, '');

                // El + solo puede estar al principio
                value = value.replace(/(?!^)\+/g, '');

                // Si comienza con números, anteponer +
                if (value && !value.startsWith('+')) {
                  value = `+${value}`;
                }

                // Máximo 12 caracteres: + + 11 números
                value = value.slice(0, 12);

                updateField(
                  'numero_telefono',
                  value
                );
              }}
              placeholder="+56912345678"
              style={inputStyle}
            />
          </div>

          {/* IMEI / PIN */}

          <div className="responsive-form-grid">
            <div>
              <label
                style={{
                  ...labelStyle,
                  color: '#166534',
                }}
              >
                IMEI *
              </label>

              <input
                aria-label="IMEI"
                required
                type="text"
                value={equipo.imei || ''}
                onChange={(e) =>
                  updateField(
                    'imei',
                    e.target.value
                  )
                }
                style={inputStyle}
              />
            </div>

            <div>
              <label
                style={{
                  ...labelStyle,
                  color: '#166534',
                }}
              >
                PIN
              </label>

              <input
                aria-label="PIN"
                type="text"
                value={equipo.pin || ''}
                onChange={(e) =>
                  updateField(
                    'pin',
                    e.target.value
                  )
                }
                style={inputStyle}
              />
            </div>
          </div>
        </div>
      )}

      {/* =========================
          TABLET / BAM
          LÍNEA MÓVIL
      ========================= */}

      {usaLineaMovil && !esCelular && (
        <div
          style={{
            backgroundColor: '#f0fdf4',
            padding: '0.8rem',
            borderRadius: '8px',
            border: '1px solid #bbf7d0',
          }}
        >
          <label
            style={{
              ...labelStyle,
              color: '#166534',
            }}
          >
            SIM / N° Celular
          </label>

          <input
            aria-label="Número de teléfono"
            type="text"
            value={
              equipo.numero_telefono || ''
            }
            onChange={(e) =>
              updateField(
                'numero_telefono',
                e.target.value
              )
            }
            placeholder="Opcional"
            style={inputStyle}
          />
        </div>
      )}

      {/* =========================
          ICLOUD MAC
      ========================= */}

      {esMac && (
        <div
          style={{
            backgroundColor: '#eff6ff',
            padding: '0.8rem',
            borderRadius: '8px',
            border: '1px solid #bfdbfe',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
          }}
        >
          <span
            style={{
              fontSize: '0.75rem',
              fontWeight: 'bold',
              color: '#1e40af',
              textTransform: 'uppercase',
            }}
          >
            Detalles de iCloud (Mac)
          </span>

          <div>
            <label
              style={{
                ...labelStyle,
                color: '#1e40af',
              }}
            >
              Cuenta iCloud
            </label>

            <input
              aria-label="Cuenta iCloud"
              type="email"
              value={
                equipo.icloud_cuenta || ''
              }
              onChange={(e) =>
                updateField(
                  'icloud_cuenta',
                  e.target.value
                )
              }
              style={inputStyle}
            />
          </div>

          <div>
            <label
              style={{
                ...labelStyle,
                color: '#1e40af',
              }}
            >
              Contraseña iCloud
            </label>

            <input
              aria-label="Contraseña iCloud"
              type="text"
              value={
                equipo.icloud_password ||
                ''
              }
              onChange={(e) =>
                updateField(
                  'icloud_password',
                  e.target.value
                )
              }
              style={inputStyle}
            />
          </div>
        </div>
      )}

      {/* =========================
          HOSTNAME
          SOLO NOTEBOOK / MAC
      ========================= */}

      {usaHostname && (
        <div>
          <label
            style={{
              ...labelStyle,
              color: '#0284c7',
            }}
          >
            Hostname
            {' '}
            (identificador del equipo) *
          </label>

          <input
            aria-label="Hostname"
            required
            type="text"
            value={equipo.hostname || ''}
            onChange={(e) =>
              onHostnameChange(
                e.target.value
              )
            }
            placeholder="Ej: CL-NB-001"
            style={inputStyle}
          />
        </div>
      )}

      {/* =========================
          ACTIVO FIJO
      ========================= */}

      <div>
        <label style={labelStyle}>
          Activo Fijo
          {' '}
          (AF - Máx. 12 caracteres)
        </label>

        <input
          aria-label="Activo fijo"
          type="text"
          maxLength={12}
          value={equipo.af || ''}
          onChange={(e) => {
            const value = e.target.value
              .replace(/[^a-zA-Z0-9]/g, '')
              .slice(0, 12);

            updateField(
              'af',
              value
            );
          }}
          placeholder="Ej: 102401000300 o SINAF"
          style={inputStyle}
        />
      </div>

      <div><label style={labelStyle}>Estado físico</label><select aria-label="Estado físico" value={equipo.estado_fisico || 'USADO'} onChange={(e) => updateField('estado_fisico', e.target.value)} style={inputStyle}><option value="NUEVO">Nuevo</option><option value="SEMINUEVO">Seminuevo</option><option value="USADO">Usado</option><option value="DANADO">Dañado</option></select></div>
      <div><label style={labelStyle}>Fecha de vencimiento de garantía (opcional)</label><input aria-label="Fecha de vencimiento de garantía" type="date" value={equipo.fecha_vencimiento_garantia || ''} onChange={(e) => updateField('fecha_vencimiento_garantia', e.target.value)} style={inputStyle} /></div>
      <div><label style={labelStyle}>Ubicación inicial</label><input aria-label="Ubicación inicial" value={equipo.ubicacion_actual || ''} maxLength={100} onChange={(e) => updateField('ubicacion_actual', e.target.value)} style={inputStyle} /></div>
      {usaHostname && <div><label style={labelStyle}>MAC Address *</label><input aria-label="MAC Address" required value={equipo.mac_address || ''} maxLength={30} onChange={(e) => updateField('mac_address', e.target.value)} style={inputStyle} placeholder="AA:BB:CC:DD:EE:FF" /></div>}

      {/* =========================
          ACCESORIOS
      ========================= */}

      <div>
        <label style={labelStyle}>
          Accesorios incluidos
        </label>

        <textarea
          aria-label="Accesorios u observaciones"
          rows={3}
          maxLength={255}
          value={equipo.accesorios || ''}
          onChange={(e) =>
            updateField(
              'accesorios',
              e.target.value
            )
          }
          placeholder="Ej: Cargador, bolso, mouse inalámbrico"
          style={{
            ...inputStyle,
            resize: 'vertical',
            fontFamily: 'inherit'
          }}
        />
      </div>

      <p style={{ color: '#475569', fontSize: '0.85rem' }}>El activo se registra disponible. Para entregarlo use «Nuevo movimiento» y se generará su acta con folio.</p>
    </>
  );
}
