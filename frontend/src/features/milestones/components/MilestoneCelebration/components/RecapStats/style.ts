import styled from 'styled-components';

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: ${({ theme }) => theme.space.sm};

  @media (max-width: 480px) {
    grid-template-columns: repeat(2, 1fr);
  }
`;

export const Tile = styled.div<{ $lead: boolean }>`
  padding: ${({ theme }) => theme.space.md};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme, $lead }) => ($lead ? theme.color.accentSoft : theme.color.surface2)};
`;

export const Value = styled.div`
  font-size: ${({ theme }) => theme.fontSize.xxl};
  font-weight: 800;
  line-height: 1.1;
  color: ${({ theme }) => theme.color.text};
`;

export const Label = styled.div`
  margin-top: 2px;
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Team = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  margin-top: ${({ theme }) => theme.space.md};
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Faces = styled.div`
  display: flex;

  & > * + * {
    margin-left: -6px;
  }
`;
