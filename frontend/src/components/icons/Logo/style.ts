import styled from 'styled-components';

export const Svg = styled.svg`
  flex: none;

  .badge {
    fill: ${({ theme }) => theme.color.radi};
  }

  .eye {
    fill: ${({ theme }) => theme.color.radiEye};
  }
`;
