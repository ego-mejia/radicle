import styled from 'styled-components';

export const Item = styled.li`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  padding: ${({ theme }) => theme.space.lg} 0;
  border-top: 1px solid ${({ theme }) => theme.color.border};
`;

export const Path = styled.span`
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Title = styled.a`
  font-size: ${({ theme }) => theme.fontSize.xl};
  font-weight: 600;
  color: ${({ theme }) => theme.color.text};
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
`;

export const Snippet = styled.p`
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: ${({ theme }) => theme.color.text};
`;

export const Tags = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.xs};
`;
