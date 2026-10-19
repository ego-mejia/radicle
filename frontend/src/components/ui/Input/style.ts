import styled, { css } from 'styled-components';

const control = css<{ $invalid?: boolean }>`
  width: 100%;
  font: inherit;
  color: ${({ theme }) => theme.color.text};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme, $invalid }) => ($invalid ? theme.color.danger : theme.color.border)};
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 7px 10px;

  &::placeholder {
    color: ${({ theme }) => theme.color.textMuted};
  }

  &:focus {
    outline: none;
    border-color: ${({ theme }) => theme.color.accent};
    box-shadow: 0 0 0 2px ${({ theme }) => theme.color.accentSoft};
  }

  &:disabled {
    opacity: 0.6;
  }
`;

export const StyledInput = styled.input<{ $invalid?: boolean }>`
  ${control}
  height: 34px;
`;

export const StyledTextarea = styled.textarea<{ $invalid?: boolean }>`
  ${control}
  min-height: 90px;
  resize: vertical;
  line-height: 1.5;
`;

export const StyledSelect = styled.select<{ $invalid?: boolean }>`
  ${control}
  height: 34px;
  padding-right: 28px;
  cursor: pointer;
`;
