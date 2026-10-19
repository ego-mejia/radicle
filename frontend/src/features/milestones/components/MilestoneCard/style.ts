import styled from 'styled-components';

export const Card = styled.article<{ $closed: boolean }>`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => theme.space.lg};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  opacity: ${({ $closed }) => ($closed ? 0.7 : 1)};
`;

export const Top = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  flex-wrap: wrap;

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.lg};
  }
`;

export const Spacer = styled.div`
  flex: 1;
`;

export const Date = styled.span<{ $late: boolean }>`
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme, $late }) => ($late ? theme.color.danger : theme.color.textMuted)};
`;

export const Bar = styled.div`
  display: flex;
  height: 8px;
  overflow: hidden;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface2};
`;

export const Segment = styled.div<{ $category: 'todo' | 'in_progress' | 'done'; $share: number }>`
  width: ${({ $share }) => $share * 100}%;
  background: ${({ theme, $category }) =>
    $category === 'done'
      ? theme.color.accentFill
      : $category === 'in_progress'
        ? theme.color.accent
        : 'transparent'};
  opacity: ${({ $category }) => ($category === 'in_progress' ? 0.5 : 1)};
`;

export const Legend = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.lg};
  flex-wrap: wrap;
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};

  span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
`;

export const Description = styled.div`
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Forecast = styled.span<{ $risk: boolean }>`
  font-weight: 600;
  color: ${({ theme, $risk }) => ($risk ? theme.color.warning : theme.color.accent)};
`;
