import styled from 'styled-components';

export const Body = styled.div`
  width: 100%;
  max-width: 1180px;
  padding-top: ${({ theme }) => theme.space.xl};
  padding-bottom: 64px;
  padding-left: max(24px, env(safe-area-inset-left, 0px));
  padding-right: max(24px, env(safe-area-inset-right, 0px));
`;
