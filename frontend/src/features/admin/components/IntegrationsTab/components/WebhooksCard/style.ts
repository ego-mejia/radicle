import styled from 'styled-components';

export const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: ${({ theme }) => theme.space.md};
`;

export const Row = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Secret = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};
  align-items: center;
  padding: ${({ theme }) => theme.space.md};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => theme.color.text};

  code {
    font-family: ${({ theme }) => theme.fonts.mono};
    word-break: break-all;
  }
`;

export const Log = styled.ul`
  list-style: none;
  margin: 0 0 ${({ theme }) => theme.space.md};
  padding: 0 0 0 ${({ theme }) => theme.space.xl};
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};

  li {
    display: flex;
    flex-wrap: wrap;
    gap: ${({ theme }) => theme.space.sm};
    align-items: center;
    font-size: ${({ theme }) => theme.fontSize.sm};
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Error = styled.span`
  flex-basis: 100%;
  color: ${({ theme }) => theme.color.danger};
`;
