import styled from 'styled-components';

export const Tag = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 3px;
  height: 22px;
  padding: 0 6px;
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => theme.color.accent};
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};

  button {
    all: unset;
    cursor: pointer;
    line-height: 1;
  }
`;

export const Add = styled.input`
  width: 90px;
  height: 24px;
  padding: 0 6px;
  border: 1px dashed ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.sm};
  background: transparent;
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.text};

  &:focus {
    outline: none;
    border-style: solid;
    border-color: ${({ theme }) => theme.color.accent};
  }
`;
