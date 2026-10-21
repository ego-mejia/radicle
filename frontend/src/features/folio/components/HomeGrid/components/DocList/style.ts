import styled from 'styled-components';

export const Section = styled.section`
  height: 100%;
  box-sizing: border-box;
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  padding: ${({ theme }) => theme.space.xl};
  display: flex;
  flex-direction: column;
`;

export const Heading = styled.h2`
  margin: 0 0 ${({ theme }) => theme.space.sm};
  font-size: 17px;
`;

export const List = styled.ol`
  list-style: none;
  margin: 0;
  padding: 0;
`;

export const Item = styled.a`
  display: flex;
  align-items: baseline;
  gap: ${({ theme }) => theme.space.lg};
  padding: ${({ theme }) => theme.space.md} 0;
  border-top: 1px solid ${({ theme }) => theme.color.surface2};
  text-decoration: none;
  color: ${({ theme }) => theme.color.text};

  &:hover strong {
    text-decoration: underline;
  }
`;

export const Number = styled.span`
  flex: 0 0 28px;
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: 20px;
  font-weight: 500;
  color: ${({ theme }) => theme.color.accent};
`;

export const Text = styled.span`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  min-width: 0;
`;

export const Kind = styled.span`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Title = styled.strong`
  font-size: ${({ theme }) => theme.fontSize.lg};
  font-weight: 600;
  line-height: 1.35;
`;

export const Meta = styled.span`
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Empty = styled.p`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
`;
