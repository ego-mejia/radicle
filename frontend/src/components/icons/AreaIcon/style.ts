import styled from 'styled-components';

export const Wrap = styled.span<{ $color: string }>`
  display: inline-grid;
  place-items: center;
  flex: none;
  color: ${({ $color }) => $color};
`;

export const Dot = styled.span`
  width: 70%;
  height: 70%;
  border-radius: 3px;
`;
