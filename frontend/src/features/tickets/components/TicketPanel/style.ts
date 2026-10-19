import styled from 'styled-components';

export const Bar = styled.div`
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  padding: 8px 12px;
  background: ${({ theme }) => theme.color.bg};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
`;

export const Body = styled.div`
  padding: ${({ theme }) => theme.space.xl};
`;
