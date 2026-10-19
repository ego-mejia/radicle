import styled from 'styled-components';

export const Columns = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xl};
  max-width: 640px;
`;

export const Chips = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Chip = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 4px 2px 8px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.full};
  font-size: ${({ theme }) => theme.fontSize.sm};

  button {
    width: 22px;
    height: 22px;
  }
`;

export const Swatch = styled.input`
  width: 16px;
  height: 16px;
  padding: 0;
  border: 0;
  background: none;
  cursor: pointer;
`;

export const Add = styled.form`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
  margin-top: ${({ theme }) => theme.space.sm};
  max-width: 360px;
`;
