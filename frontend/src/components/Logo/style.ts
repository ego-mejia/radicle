import styled from 'styled-components';

export const Svg = styled.svg`
  flex: none;

  .badge {
    fill: ${({ theme }) => theme.color.accentFill};
  }

  .mark {
    fill: none;
    stroke: ${({ theme }) => theme.color.onAccent};
    stroke-width: 2.2;
    stroke-linecap: round;
  }
`;
