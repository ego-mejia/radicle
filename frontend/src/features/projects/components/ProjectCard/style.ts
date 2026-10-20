import styled from 'styled-components';

export const Card = styled.a`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => theme.space.lg};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  color: ${({ theme }) => theme.color.text};
  text-decoration: none;
  transition: border-color 0.12s;

  &:hover {
    border-color: ${({ theme }) => theme.color.accent};
  }
`;

export const Top = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Name = styled.div`
  font-size: ${({ theme }) => theme.fontSize.lg};
  font-weight: 700;
`;

export const Meta = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Wrap = styled.div`
  position: relative;
  display: flex;
  flex-direction: column;

  > a {
    flex: 1;
  }
`;

export const Edit = styled.div`
  position: absolute;
  top: 10px;
  right: 10px;
  opacity: 0;
  transition: opacity 0.12s;

  ${Wrap}:hover &,
  &:focus-within {
    opacity: 1;
  }

  @media (hover: none) {
    opacity: 1;
  }
`;

export const Role = styled.span<{ $room: boolean }>`
  margin-right: ${({ $room }) => ($room ? '28px' : 0)};
`;
