import styled from 'styled-components';

export const Row = styled.div`
  display: grid;
  grid-template-columns: 110px minmax(0, 1fr);
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  min-height: 32px;
`;

export const Label = styled.span`
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Value = styled.div`
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
`;

export const Bare = styled.select`
  flex: 1 1 auto;
  min-width: 0;
  max-width: 100%;
  height: 28px;
  padding: 0 6px;
  border: 1px solid transparent;
  border-radius: ${({ theme }) => theme.radius.sm};
  background: transparent;
  font: inherit;
  color: ${({ theme }) => theme.color.text};
  cursor: pointer;

  &:hover:not(:disabled),
  &:focus {
    border-color: ${({ theme }) => theme.color.border};
    background: ${({ theme }) => theme.color.surface};
    outline: none;
  }

  &:disabled {
    cursor: default;
    opacity: 1;
    appearance: none;
  }
`;

export const BareInput = styled.input`
  width: 100%;
  max-width: 180px;
  height: 28px;
  padding: 0 6px;
  border: 1px solid transparent;
  border-radius: ${({ theme }) => theme.radius.sm};
  background: transparent;
  font: inherit;
  color: ${({ theme }) => theme.color.text};

  &:hover:not(:disabled),
  &:focus {
    border-color: ${({ theme }) => theme.color.border};
    background: ${({ theme }) => theme.color.surface};
    outline: none;
  }
`;
