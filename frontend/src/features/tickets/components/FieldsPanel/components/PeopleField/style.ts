import styled from 'styled-components';

export const Person = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  padding: 2px 6px 2px 2px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface2};
  font-size: ${({ theme }) => theme.fontSize.sm};

  button {
    all: unset;
    display: inline-grid;
    place-items: center;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    cursor: pointer;
    color: ${({ theme }) => theme.color.textMuted};
  }

  button:hover {
    color: ${({ theme }) => theme.color.danger};
  }

  svg {
    width: 12px;
    height: 12px;
  }
`;

export const Picker = styled.span`
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  width: 100%;
`;
