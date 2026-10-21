import styled from 'styled-components';

export const Page = styled.div`
  min-height: 100%;
  background: ${({ theme }) => theme.color.bg};
`;

export const Progress = styled.div`
  position: sticky;
  top: 0;
  z-index: 20;
  height: 3px;
  background: ${({ theme }) => theme.color.border};
`;

export const Fill = styled.div`
  height: 3px;
  background: ${({ theme }) => theme.color.accent};
  transition: width 80ms linear;
`;

export const Bar = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => `${theme.space.md} 28px`};

  @media (max-width: 600px) {
    padding: ${({ theme }) => `${theme.space.sm} ${theme.space.lg}`};
  }
`;

export const BarTitle = styled.span`
  flex: 1 1 200px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Left = styled.span`
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Exit = styled.button`
  min-height: 36px;
  padding: 0 ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  cursor: pointer;
`;

export const Column = styled.article`
  max-width: 660px;
  margin: 0 auto;
  padding: 40px 28px 96px;
  display: flex;
  flex-direction: column;
  gap: 24px;

  @media (max-width: 600px) {
    padding: ${({ theme }) => `${theme.space.xl} ${theme.space.lg} 64px`};
  }
`;

export const Kicker = styled.span`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.color.accent};
`;

export const Title = styled.h1`
  margin: 0;
  font-size: 42px;
  line-height: 1.1;
  letter-spacing: -0.025em;

  @media (max-width: 600px) {
    font-size: 32px;
  }
`;

export const Lead = styled.p`
  margin: 0;
  font-size: 20px;
  line-height: 1.65;
  color: ${({ theme }) => theme.color.textMuted};
`;
