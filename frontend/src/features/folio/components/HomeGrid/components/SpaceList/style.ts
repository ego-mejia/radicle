import styled from 'styled-components';

export { Empty, Heading, Section } from '../DocList/style';

export const List = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
`;

export const Item = styled.a`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => theme.space.sm} 0;
  min-height: 44px;
  text-decoration: none;
  color: ${({ theme }) => theme.color.text};

  &:hover span:nth-child(2) {
    text-decoration: underline;
  }
`;

export const Letter = styled.span`
  flex: 0 0 32px;
  height: 32px;
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => theme.color.text};
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Name = styled.span`
  flex: 1;
  min-width: 0;
  font-size: 14px;
  font-weight: 500;
`;

export const Count = styled.span`
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;
