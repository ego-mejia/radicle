import styled from 'styled-components';

export const Canvas = styled.div`
  position: relative;
  height: 100%;
  min-height: 320px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  overflow: hidden;
`;
