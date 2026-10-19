import { forwardRef } from 'react';
import { StyledInput, StyledSelect, StyledTextarea } from './style';

type InputProps = React.InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean };

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { invalid, ...rest },
  ref,
) {
  return <StyledInput ref={ref} $invalid={invalid} aria-invalid={invalid || undefined} {...rest} />;
});

type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & { invalid?: boolean };

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { invalid, ...rest },
  ref,
) {
  return <StyledTextarea ref={ref} $invalid={invalid} {...rest} />;
});

type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement> & { invalid?: boolean };

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { invalid, ...rest },
  ref,
) {
  return <StyledSelect ref={ref} $invalid={invalid} {...rest} />;
});
