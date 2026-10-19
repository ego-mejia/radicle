import styled, { css } from 'styled-components';

export type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type Size = 'md' | 'sm';

const variants = {
  primary: css`
    background: ${({ theme }) => theme.color.accentFill};
    border-color: ${({ theme }) => theme.color.accentFill};
    color: ${({ theme }) => theme.color.onAccent};
    &:hover:not(:disabled) {
      filter: brightness(0.95);
    }
  `,
  secondary: css`
    background: ${({ theme }) => theme.color.surface};
    border-color: ${({ theme }) => theme.color.border};
    color: ${({ theme }) => theme.color.text};
    &:hover:not(:disabled) {
      background: ${({ theme }) => theme.color.surface2};
    }
  `,
  ghost: css`
    background: transparent;
    border-color: transparent;
    color: ${({ theme }) => theme.color.textMuted};
    &:hover:not(:disabled) {
      background: ${({ theme }) => theme.color.surface2};
      color: ${({ theme }) => theme.color.text};
    }
  `,
  danger: css`
    background: transparent;
    border-color: ${({ theme }) => theme.color.danger};
    color: ${({ theme }) => theme.color.danger};
    &:hover:not(:disabled) {
      background: ${({ theme }) => theme.color.danger};
      color: #fff;
    }
  `,
};

export const Base = styled.button<{ $variant: Variant; $size: Size; $block: boolean }>`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: ${({ $size }) => ($size === 'sm' ? '28px' : '34px')};
  padding: 0 ${({ $size }) => ($size === 'sm' ? '10px' : '14px')};
  width: ${({ $block }) => ($block ? '100%' : 'auto')};
  border: 1px solid;
  border-radius: ${({ theme }) => theme.radius.md};
  font: inherit;
  font-size: ${({ theme, $size }) => ($size === 'sm' ? theme.fontSize.sm : theme.fontSize.md)};
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  transition:
    background 0.12s,
    color 0.12s,
    filter 0.12s;
  ${({ $variant }) => variants[$variant]}

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  svg {
    width: 15px;
    height: 15px;
    flex: none;
  }
`;

export const Icon = styled.button<{ $active: boolean }>`
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme, $active }) => ($active ? theme.color.surface2 : 'transparent')};
  color: ${({ theme }) => theme.color.textMuted};
  cursor: pointer;

  &:hover:not(:disabled) {
    background: ${({ theme }) => theme.color.surface2};
    color: ${({ theme }) => theme.color.text};
  }

  svg {
    width: 16px;
    height: 16px;
  }
`;
