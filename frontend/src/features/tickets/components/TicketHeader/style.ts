import styled from 'styled-components';

export const Header = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

export const Top = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  flex-wrap: wrap;
`;

export const Spacer = styled.div`
  flex: 1;
`;

export const Title = styled.h1`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.xxl};
  line-height: 1.25;
  letter-spacing: -0.01em;
  overflow-wrap: anywhere;
`;

export const TitleButton = styled.button`
  all: unset;
  display: block;
  border-radius: ${({ theme }) => theme.radius.sm};
  cursor: text;

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
  }

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.color.accent};
  }
`;

export const TitleInput = styled.input`
  width: 100%;
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.xxl};
  font-weight: 700;
  letter-spacing: -0.01em;
  color: ${({ theme }) => theme.color.text};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.accent};
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 2px 6px;

  &:focus {
    outline: none;
  }
`;
