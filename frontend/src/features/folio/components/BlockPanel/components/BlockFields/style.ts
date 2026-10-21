import styled from 'styled-components';

export const Row = styled.div`
  display: grid;
  grid-template-columns: 1fr 140px;
  gap: ${({ theme }) => theme.space.md};
`;

export const Code = styled.textarea`
  width: 100%;
  padding: ${({ theme }) => theme.space.sm};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme }) => theme.color.surface2};
  color: ${({ theme }) => theme.color.text};
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
  resize: vertical;
`;
