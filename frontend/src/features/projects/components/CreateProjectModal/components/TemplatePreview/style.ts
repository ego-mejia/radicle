import styled from 'styled-components';

export const Box = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 72px;
  padding: ${({ theme }) => theme.space.md};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface2};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Line = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;

  strong {
    min-width: 64px;
    font-weight: 600;
  }
`;

export const Status = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 3px;
`;
