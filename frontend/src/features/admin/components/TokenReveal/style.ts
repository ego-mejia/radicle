import styled from 'styled-components';

export const Box = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

export const Warning = styled.strong`
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => (theme.mode === 'dark' ? theme.color.accent : theme.color.onAccent)};
`;

export const Code = styled.div`
  display: flex;
  align-items: flex-start;
  gap: ${({ theme }) => theme.space.sm};

  pre {
    flex: 1;
    min-width: 0;
    margin: 0;
    padding: 8px 10px;
    overflow-x: auto;
    border-radius: ${({ theme }) => theme.radius.md};
    background: ${({ theme }) => theme.color.surface};
    border: 1px solid ${({ theme }) => theme.color.border};
    font-family: ${({ theme }) => theme.fonts.mono};
    font-size: ${({ theme }) => theme.fontSize.sm};
    white-space: pre;
  }
`;

export const Label = styled.div`
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  color: ${({ theme }) => theme.color.textMuted};
`;
