import * as S from './style';

export function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <S.Row>
      <S.Label>{label}</S.Label>
      <S.Value>{children}</S.Value>
    </S.Row>
  );
}

type Option = { value: string; label: string };

type SelectProps = {
  label: string;
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  disabled?: boolean;
};

/** A select that looks like text until hovered; for inline editing. */
export function InlineSelect({ label, value, options, onChange, disabled }: SelectProps) {
  return (
    <S.Bare
      aria-label={label}
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </S.Bare>
  );
}

type InputProps = {
  label: string;
  value: string;
  type?: 'text' | 'date' | 'number';
  onCommit: (value: string) => void;
  disabled?: boolean;
  placeholder?: string;
};

/** Text-like inline input that saves on blur or Enter. */
export function InlineInput({
  label,
  value,
  type = 'text',
  onCommit,
  disabled,
  placeholder,
}: InputProps) {
  return (
    <S.BareInput
      key={value}
      aria-label={label}
      type={type}
      defaultValue={value}
      disabled={disabled}
      placeholder={placeholder}
      step={type === 'number' ? '0.5' : undefined}
      min={type === 'number' ? 0 : undefined}
      onBlur={(e) => e.target.value !== value && onCommit(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
      }}
    />
  );
}
