import styled from 'styled-components';

export const Palette = styled.section`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Label = styled.h3`
  margin: 0 ${({ theme }) => theme.space.sm} 0 0;
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Item = styled.button`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  min-height: 32px;
  padding: 0 ${({ theme }) => theme.space.md};
  border: 1px dashed ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  font-size: ${({ theme }) => theme.fontSize.sm};
  cursor: pointer;

  &:hover {
    border-color: ${({ theme }) => theme.color.accent};
  }

  svg {
    width: 14px;
    height: 14px;
  }
`;
