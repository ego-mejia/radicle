import styled from 'styled-components';

export const Button = styled.button`
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 60;
  width: 64px;
  height: 64px;
  padding: 0;
  border: 0;
  background: none;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;

  &:focus-visible {
    outline: 3px solid ${({ theme }) => theme.color.accent};
    outline-offset: 2px;
    border-radius: 50%;
  }

  @media print {
    display: none;
  }
`;

export const Art = styled.span`
  display: block;
  width: 100%;
  height: 100%;
  pointer-events: none;

  svg {
    display: block;
    width: 100%;
    height: 100%;
    overflow: visible;
  }
`;
