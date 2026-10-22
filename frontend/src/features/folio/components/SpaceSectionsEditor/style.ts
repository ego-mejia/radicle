import styled from 'styled-components';

export const Card = styled.section`
  max-width: 640px;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  padding: 20px 22px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 16px;
  background: ${({ theme }) => theme.color.surface};
`;

export const Intro = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;

  span {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const List = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;

  li {
    display: flex;
    align-items: center;
    gap: ${({ theme }) => theme.space.md};
    min-height: 48px;
    border-top: 1px solid ${({ theme }) => theme.color.surface2};
  }
  small {
    margin-left: auto;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Check = styled.span`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  font-weight: 600;

  input {
    width: 16px;
    height: 16px;
    accent-color: ${({ theme }) => theme.color.accent};
  }
`;

export const Moves = styled.span`
  display: flex;
  gap: 4px;
`;

export const Move = styled.button`
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  cursor: pointer;

  svg {
    width: 15px;
    height: 15px;
  }
  &:disabled {
    opacity: 0.4;
    cursor: default;
  }
`;

export const Error = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.danger};
`;
