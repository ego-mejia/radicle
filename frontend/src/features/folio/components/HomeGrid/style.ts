import styled from 'styled-components';

/** Rows grow with their content; `h` only sets how many a block spans at least. */
export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  grid-auto-rows: minmax(48px, auto);
  gap: ${({ theme }) => theme.space.xl};

  @media (max-width: 860px) {
    grid-template-columns: minmax(0, 1fr);
  }
`;

type Place = { $x: number; $y: number; $w: number; $h: number };

export const Cell = styled.div<Place>`
  grid-column: ${({ $x, $w }) => `${$x + 1} / span ${$w}`};
  grid-row: ${({ $y, $h }) => `${$y + 1} / span ${$h}`};
  min-width: 0;
  display: flex;
  flex-direction: column;

  & > * {
    flex: 1;
  }

  @media (max-width: 860px) {
    grid-column: auto;
    grid-row: auto;
  }
`;
