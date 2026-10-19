import styled from 'styled-components';

export const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Big = styled.div`
  font-size: 36px;
  font-weight: 700;
  line-height: 1;
`;

export const Bar = styled.div`
  height: 10px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface2};
  overflow: hidden;

  span {
    display: block;
    height: 100%;
    background: ${({ theme }) => theme.color.catDone};
  }
`;

export const Line = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const State = styled.p<{ $risk: boolean }>`
  margin: 0;
  font-weight: 600;
  color: ${({ theme, $risk }) => ($risk ? theme.color.warning : theme.color.accent)};
`;
