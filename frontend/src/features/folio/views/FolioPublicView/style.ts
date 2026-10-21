import styled from 'styled-components';

export const Page = styled.div`
  min-height: 100vh;
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
`;

export const Bar = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => `${theme.space.md} ${theme.space.xxl}`};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};

  @media (max-width: 600px) {
    padding: ${({ theme }) => `${theme.space.sm} ${theme.space.lg}`};
  }
`;

export const Space = styled.p`
  margin: 0;
  font-weight: 600;

  a {
    color: inherit;
    text-decoration: none;
  }
`;

export const Badge = styled.span`
  padding: 2px 10px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.full};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Body = styled.div<{ $withNav: boolean }>`
  display: grid;
  grid-template-columns: ${({ $withNav }) => ($withNav ? '240px minmax(0, 1fr)' : '1fr')};

  @media (max-width: 900px) {
    grid-template-columns: 1fr;
  }
`;

export const Nav = styled.nav`
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: ${({ theme }) => theme.space.xl};
  border-right: 1px solid ${({ theme }) => theme.color.border};

  @media (max-width: 900px) {
    border-right: 0;
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
  }
`;

export const Folder = styled.span<{ $depth: number }>`
  padding: ${({ theme }) => theme.space.xs} 0;
  padding-left: ${({ $depth }) => $depth * 14}px;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  text-transform: uppercase;
  letter-spacing: 0.04em;
`;

export const NavItem = styled.span<{ $depth: number }>`
  display: flex;
  margin-left: ${({ $depth }) => $depth * 14}px;

  a {
    flex: 1;
    min-width: 0;
    padding: ${({ theme }) => `${theme.space.xs} ${theme.space.sm}`};
    border-radius: ${({ theme }) => theme.radius.md};
    color: ${({ theme }) => theme.color.text};
    text-decoration: none;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  a:hover,
  a[aria-current='page'] {
    background: ${({ theme }) => theme.color.surface2};
  }
`;

export const Index = styled.section`
  max-width: 720px;
  margin: 0 auto;
  padding: 64px ${({ theme }) => theme.space.xxl};

  h1 {
    margin: 0 0 ${({ theme }) => theme.space.lg};
  }

  p {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;
