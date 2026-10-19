import styled from 'styled-components';

export const Grid = styled.div`
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
  gap: ${({ theme }) => theme.space.xl};

  @media (max-width: 1100px) {
    grid-template-columns: minmax(0, 1fr);
  }
`;

export const Column = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  min-width: 0;
`;

export const Heading = styled.h3`
  margin: ${({ theme }) => theme.space.sm} 0 0;
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
  font-weight: 600;
`;

export const Error = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.danger};
`;

export const Warning = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.warning};
`;
