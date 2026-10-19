import styled from 'styled-components';

export const Section = styled.section`
  display: flex;
  flex-direction: column;
  gap: 6px;
`;

export const Head = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.lg};
  }
`;

export const Muted = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Spacer = styled.span`
  flex: 1;
`;

export const Goal = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Capacity = styled.div<{ $over: boolean }>`
  position: relative;
  height: 20px;
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme }) => theme.color.surface2};
  overflow: hidden;
  max-width: 420px;

  span {
    position: relative;
    padding: 0 8px;
    font-size: ${({ theme }) => theme.fontSize.sm};
    line-height: 20px;
    font-weight: ${({ $over }) => ($over ? 700 : 400)};
    color: ${({ theme, $over }) => ($over ? theme.color.warning : theme.color.text)};
  }
`;

export const Bar = styled.div<{ $over: boolean }>`
  position: absolute;
  inset: 0 auto 0 0;
  background: ${({ theme, $over }) => ($over ? theme.color.warning : theme.color.accentSoft)};
  opacity: ${({ $over }) => ($over ? 0.35 : 1)};
`;

export const Warning = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.warning};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const List = styled.div<{ $over: boolean }>`
  border: 1px ${({ $over }) => ($over ? 'dashed' : 'solid')}
    ${({ theme, $over }) => ($over ? theme.color.accent : theme.color.border)};
  border-radius: ${({ theme }) => theme.radius.md};
  min-height: 48px;
  overflow: hidden;
`;

export const Empty = styled.p`
  margin: 0;
  padding: ${({ theme }) => theme.space.md};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;
