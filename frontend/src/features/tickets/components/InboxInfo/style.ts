import styled from 'styled-components';

export const Box = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => theme.space.sm} ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface2};
  font-size: ${({ theme }) => theme.fontSize.md};

  label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  select {
    font: inherit;
    padding: 2px 4px;
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: ${({ theme }) => theme.radius.sm};
    background: ${({ theme }) => theme.color.surface};
    color: ${({ theme }) => theme.color.text};
  }
`;

export const Badge = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  align-self: flex-start;
  padding: 2px 10px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.accentSoft};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;
