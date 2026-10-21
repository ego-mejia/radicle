import styled from 'styled-components';

/** Fixed at the selection, in viewport coordinates. */
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
  border: 0;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.accentFill};
  color: ${({ theme }) => theme.color.onAccent};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  font-weight: 600;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
  cursor: pointer;

  svg {
    width: 16px;
    height: 16px;
  }
`;

export const Box = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  width: min(360px, calc(100vw - 32px));
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface};
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
`;

export const Quote = styled.p`
  margin: 0;
  padding-left: ${({ theme }) => theme.space.sm};
  border-left: 3px solid ${({ theme }) => theme.color.accent};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Row = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: ${({ theme }) => theme.space.sm};
`;
