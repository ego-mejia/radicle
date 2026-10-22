import styled from 'styled-components';

export { AppShell as Shell } from '../../components/layout/AppSidebar/style';

export const Main = styled.div`
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 100vh;
`;

export const Content = styled.main`
  flex: 1;
  min-width: 0;
  padding: ${({ theme }) => theme.space.xl};

  @media (max-width: 600px) {
    padding: ${({ theme }) => theme.space.lg};
  }
`;

export const SkipLink = styled.a`
  position: absolute;
  left: -999px;
  top: 8px;
  z-index: 70;
  padding: 6px 10px;
  background: ${({ theme }) => theme.color.accentFill};
  color: ${({ theme }) => theme.color.onAccent};
  border-radius: ${({ theme }) => theme.radius.md};

  &:focus {
    left: 8px;
  }
`;
