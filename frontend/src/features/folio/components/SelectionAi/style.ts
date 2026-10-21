import styled from 'styled-components';

/** Fixed above the selection, in viewport coordinates. */
export const Float = styled.div`
  position: fixed;
  z-index: 50; /* above the full-screen editor (40) */
`;

export const Trigger = styled.button`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  min-height: 32px;
  padding: ${({ theme }) => `0 ${theme.space.md}`};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  font-weight: 600;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
  cursor: pointer;

  svg {
    width: 16px;
    height: 16px;
    color: ${({ theme }) => theme.color.accent};
  }
`;

export const Box = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  width: min(420px, calc(100vw - 32px));
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface};
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
`;

export const Proposal = styled.p`
  margin: 0;
  max-height: 240px;
  overflow-y: auto;
  padding: ${({ theme }) => theme.space.sm};
  border: 1px dashed ${({ theme }) => theme.color.accent};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.accentSoft};
  white-space: pre-wrap;
`;

export const Muted = styled.p`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Error = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.danger};
`;

export const Row = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: ${({ theme }) => theme.space.sm};
`;
