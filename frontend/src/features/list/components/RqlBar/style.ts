import styled from 'styled-components';

export const Wrap = styled.form`
  position: relative;
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
  margin-bottom: ${({ theme }) => theme.space.sm};
`;

export const Field = styled.div`
  position: relative;
  flex: 1;
  min-width: 0;
`;

const text = `
  font-size: 13px;
  line-height: 20px;
  padding: 7px 10px;
  letter-spacing: 0;
  white-space: pre;
  font-variant-ligatures: none;
`;

export const Input = styled.input<{ $invalid: boolean }>`
  position: relative;
  width: 100%;
  height: 36px;
  ${text}
  font-family: ${({ theme }) => theme.fonts.mono};
  color: ${({ theme }) => theme.color.text};
  background: transparent;
  border: 1px solid ${({ theme, $invalid }) => ($invalid ? theme.color.danger : theme.color.border)};
  border-radius: ${({ theme }) => theme.radius.md};
  z-index: 1;

  &:focus {
    outline: none;
    border-color: ${({ theme, $invalid }) => ($invalid ? theme.color.danger : theme.color.accent)};
    box-shadow: 0 0 0 2px ${({ theme }) => theme.color.accentSoft};
  }
`;

/** Same metrics as the input, painted behind it, to underline the error position. */
export const Mirror = styled.div`
  position: absolute;
  inset: 0;
  overflow: hidden;
  border: 1px solid transparent;
  ${text}
  font-family: ${({ theme }) => theme.fonts.mono};
  color: transparent;
  background: ${({ theme }) => theme.color.surface};
  border-radius: ${({ theme }) => theme.radius.md};
  pointer-events: none;

  mark {
    color: transparent;
    background: none;
    text-decoration: underline wavy ${({ theme }) => theme.color.danger};
    text-underline-offset: 4px;
  }
`;

export const Error = styled.div`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.danger};
  margin-bottom: ${({ theme }) => theme.space.sm};
`;

export const Warning = styled.div`
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.warning};
`;

export const Suggestions = styled.ul`
  position: absolute;
  top: 40px;
  left: 0;
  min-width: 240px;
  max-height: 280px;
  overflow: auto;
  margin: 0;
  padding: 4px;
  list-style: none;
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
  z-index: 20;
`;

export const Suggestion = styled.li<{ $active: boolean }>`
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 5px 8px;
  border-radius: ${({ theme }) => theme.radius.sm};
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
  background: ${({ theme, $active }) => ($active ? theme.color.surface2 : 'transparent')};
  cursor: pointer;

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;
