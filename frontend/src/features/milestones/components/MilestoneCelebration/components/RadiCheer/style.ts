import styled from 'styled-components';

// Room above for his jumps: without it the dialog cuts off his top and he looks squashed.
export const Art = styled.span`
  display: block;
  width: 112px;
  height: 112px;
  margin: 32px auto 0;

  svg {
    display: block;
    width: 100%;
    height: 100%;
    overflow: visible;
  }
`;
