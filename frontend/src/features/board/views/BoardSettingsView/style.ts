import styled from 'styled-components';

export const Page = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  padding: ${({ theme }) => theme.space.xl};
  max-width: 960px;

  @media (max-width: 640px) {
    padding: ${({ theme }) => theme.space.lg};
  }
`;

export const Header = styled.header`
  display: grid;
  grid-template-columns: 1fr auto;
  gap: ${({ theme }) => theme.space.xs} ${({ theme }) => theme.space.lg};
  align-items: center;

  > a {
    grid-column: 1 / -1;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.sm};
    text-decoration: none;
  }

  h1 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.xxl};
  }
`;

export const Actions = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: ${({ theme }) => theme.space.md};
`;

export const Checks = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.md};

  label {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
`;
