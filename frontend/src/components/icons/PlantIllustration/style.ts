import styled from 'styled-components';

export const Svg = styled.svg`
  fill: none;
  stroke: ${({ theme }) => theme.color.textMuted};
  stroke-width: 1.4;
  stroke-linecap: round;
  stroke-linejoin: round;

  .accent {
    stroke: ${({ theme }) => theme.color.accent};
  }
`;
