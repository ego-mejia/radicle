import styled from 'styled-components';

export const Layout = styled.div`
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: ${({ theme }) => theme.space.xl};
  padding-bottom: ${({ theme }) => theme.space.xl};

  @media (max-width: 760px) {
    grid-template-columns: 1fr;
  }
`;

export const Nav = styled.nav`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};

  h2 {
    margin: 0 0 ${({ theme }) => theme.space.xs};
    font-size: ${({ theme }) => theme.fontSize.sm};
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: ${({ theme }) => theme.color.textMuted};
  }

  a {
    display: block;
    padding: 6px ${({ theme }) => theme.space.sm};
    border-radius: ${({ theme }) => theme.radius.md};
    color: ${({ theme }) => theme.color.text};
    text-decoration: none;
  }

  a[aria-current='page'] {
    background: ${({ theme }) => theme.color.accentSoft};
    font-weight: 600;
  }

  @media (max-width: 760px) {
    flex-direction: row;
    flex-wrap: wrap;

    > div {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }

    h2 {
      width: 100%;
    }
  }
`;

export const Main = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  min-width: 0;
`;

export const Head = styled.header`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: ${({ theme }) => theme.space.md};

  h1 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.xl};
  }

  p {
    margin: 4px 0 0;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Csv = styled.a`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  text-decoration: none;
  white-space: nowrap;
`;

export const Chart = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  padding: ${({ theme }) => theme.space.lg};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
`;

export const Error = styled.p`
  color: ${({ theme }) => theme.color.danger};
`;
