import styled from 'styled-components';

export const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Toolbar = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Status = styled.p`
  flex: 1;
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Modes = styled.div`
  display: inline-flex;
  gap: ${({ theme }) => theme.space.xs};
`;

export const Errors = styled.ul`
  margin: 0;
  padding: ${({ theme }) => theme.space.md} ${({ theme }) => theme.space.xl};
  border: 1px solid ${({ theme }) => theme.color.danger};
  border-radius: ${({ theme }) => theme.radius.md};
  color: ${({ theme }) => theme.color.danger};
  font-size: ${({ theme }) => theme.fontSize.md};
`;

/** The canvas and, beside it, the selected block's settings; stacked on narrow screens. */
export const Body = styled.div`
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  align-items: start;
  gap: ${({ theme }) => theme.space.lg};

  @media (max-width: 1100px) {
    grid-template-columns: minmax(0, 1fr);
  }
`;

export const Hint = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.md};
`;
