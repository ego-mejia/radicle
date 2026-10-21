import styled from 'styled-components';

export const Chat = styled.div<{ $compact: boolean }>`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  height: 100%;
  min-height: ${({ $compact }) => ($compact ? '220px' : '0')};
`;

export const Lines = styled.div`
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  overflow-y: auto;
  min-height: 0;
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Hint = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Question = styled.p`
  align-self: flex-end;
  max-width: 85%;
  margin: 0;
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => theme.color.text};
  overflow-wrap: anywhere;
`;

export const Error = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.danger};
`;

export const Thinking = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-style: italic;
`;

export const Compose = styled.form`
  display: flex;
  align-items: flex-end;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Input = styled.textarea`
  flex: 1;
  min-width: 0;
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  resize: none;

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.color.accent};
    outline-offset: 1px;
  }
`;
