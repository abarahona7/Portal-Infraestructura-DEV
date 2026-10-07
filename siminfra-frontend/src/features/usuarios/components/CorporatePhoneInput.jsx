import { getCorporateLineDigits, normalizeCorporateLineInput } from '../../../utils/userCorporateLines';
import './CorporatePhoneInput.css';

export default function CorporatePhoneInput({ label, value, onChange, disabled = false, inputStyle }) {
  const legacyValue = value && !String(value).startsWith('+569') ? String(value) : '';

  return <>
    <div className="corporate-phone-field" style={{ marginTop: inputStyle?.marginTop }}>
      <span aria-hidden="true">+569</span>
      <input
        aria-label={label}
        type="tel"
        inputMode="numeric"
        autoComplete="tel-national"
        maxLength={8}
        pattern="[0-9]{8}"
        placeholder="12345678"
        value={getCorporateLineDigits(value)}
        disabled={disabled}
        onChange={(event) => onChange(normalizeCorporateLineInput(event.target.value))}
        onPaste={(event) => {
          const pasted = event.clipboardData.getData('text');
          if (/^\+?56[\s-]*9/.test(pasted.trim())) {
            event.preventDefault();
            onChange(normalizeCorporateLineInput(pasted));
          }
        }}
      />
    </div>
    {legacyValue && <small>Número anterior: {legacyValue}. Ingresa los ocho dígitos para reemplazarlo.</small>}
  </>;
}
