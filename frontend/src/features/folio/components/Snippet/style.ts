import styled from 'styled-components';

export const Text = styled.span`
  mark {
    background: ${({ theme }) => theme.color.accentSoft};
    color: inherit;
    border-radius: ${({ theme }) => theme.radius.sm};
    padding: 0 2px;
  }
`;
