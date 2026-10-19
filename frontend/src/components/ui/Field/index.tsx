import { cloneElement, isValidElement, useId } from 'react';
import * as S from './style';

type Props = {
  label: string;
  hint?: string;
  error?: string | null;
  children: React.ReactNode;
  /** For several controls (e.g. radio buttons): a labelled group instead of a <label>. */
  group?: boolean;
};

/**
 * Label + control + hint or error. The label points at the control with htmlFor, so the
 * control's accessible name is just the label, not the label plus the current value.
 */
export function Field({ label, hint, error, children, group = false }: Props) {
  const id = useId();
  const messageId = `${id}-message`;
  const message = error ? (
    <S.Error id={messageId} role="alert">
      {error}
    </S.Error>
  ) : hint ? (
    <S.Hint id={messageId}>{hint}</S.Hint>
  ) : null;

  if (group) {
    return (
      <S.Wrapper role="group" aria-labelledby={`${id}-label`}>
        <S.Label id={`${id}-label`}>{label}</S.Label>
        {children}
        {message}
      </S.Wrapper>
    );
  }

  const control = isValidElement<{ id?: string; 'aria-describedby'?: string }>(children)
    ? cloneElement(children, {
        id: children.props.id ?? id,
        'aria-describedby': message ? messageId : undefined,
      })
    : children;
  const controlId = isValidElement<{ id?: string }>(children)
    ? (children.props.id ?? id)
    : undefined;

  return (
    <S.Wrapper>
      <S.Label as="label" htmlFor={controlId}>
        {label}
      </S.Label>
      {control}
      {message}
    </S.Wrapper>
  );
}

export function FormError({ children }: { children?: React.ReactNode }) {
  if (!children) return null;
  return <S.FormError role="alert">{children}</S.FormError>;
}
