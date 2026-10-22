import styled from 'styled-components';

export const Row = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Chip = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px 4px 10px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => theme.color.text};
  font-size: ${({ theme }) => theme.fontSize.md};
  font-weight: 600;

  button {
    display: grid;
    place-items: center;
    width: 22px;
    height: 22px;
    padding: 0;
    border: 0;
    border-radius: ${({ theme }) => theme.radius.full};
    background: ${({ theme }) => theme.color.surface2};
    color: inherit;
    cursor: pointer;
  }

  svg {
    width: 12px;
    height: 12px;
  }
`;

export const Summary = styled.span`
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Clear = styled.button`
  padding: 0;
  border: 0;
  background: none;
  color: ${({ theme }) => theme.color.accent};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  font-weight: 600;
  cursor: pointer;
`;
