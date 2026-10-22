import styled from 'styled-components';

export const Pages = styled.div`
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
`;

// Each page of the export starts on a new sheet of paper.
export const Sheet = styled.div`
  & + & {
    break-before: page;
  }
`;

export const Failed = styled.p`
  padding: ${({ theme }) => theme.space.xl};
  color: ${({ theme }) => theme.color.danger};
`;
