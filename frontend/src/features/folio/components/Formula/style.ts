import styled, { css } from 'styled-components';

const failed = css`
  &[data-failed] {
    color: ${({ theme }) => theme.color.danger};
    font-family: ${({ theme }) => theme.fonts.mono};
  }
`;

export const Block = styled.div`
  overflow-x: auto;
  text-align: center;
  color: ${({ theme }) => theme.color.text};
  ${failed}
`;

export const Inline = styled.span`
  ${failed}
`;
