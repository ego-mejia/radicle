import styled from 'styled-components';

export const Empty = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Name = styled.span<{ $archived: boolean }>`
  font-weight: 500;
  text-decoration: ${({ $archived }) => ($archived ? 'line-through' : 'none')};
`;

export const Key = styled.code`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-variant-ligatures: none;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Scope = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 40%;
`;
