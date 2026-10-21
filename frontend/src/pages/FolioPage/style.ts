import styled from 'styled-components';

export const Shell = styled.div`
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: ${({ theme }) => theme.color.bg};
`;

export const Bar = styled.header`
  position: sticky;
  top: 0;
  z-index: 30;
  background: ${({ theme }) => theme.color.surface};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
`;

export const BarInner = styled.div`
  max-width: 1280px;
  margin: 0 auto;
  padding: ${({ theme }) => `${theme.space.md} ${theme.space.xxl}`};
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.lg};

  @media (max-width: 600px) {
    padding: ${({ theme }) => `${theme.space.sm} ${theme.space.lg}`};
  }
`;

export const Search = styled.div`
  flex: 1 1 280px;
  min-width: 0;
`;

export const AdminLink = styled.a`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  color: ${({ theme }) => theme.color.text};
  font-size: ${({ theme }) => theme.fontSize.md};
  text-decoration: none;

  &:hover,
  &[data-status='active'] {
    background: ${({ theme }) => theme.color.surface2};
  }

  svg {
    width: 16px;
    height: 16px;
  }
`;

export const Profile = styled.button`
  display: inline-flex;
  padding: 0;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.full};
  background: none;
  cursor: pointer;

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.color.accent};
    outline-offset: 2px;
  }
`;

export const Content = styled.main`
  flex: 1;
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  box-sizing: border-box;
  padding: ${({ theme }) => `${theme.space.xl} ${theme.space.xxl}`};

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
