import styled from 'styled-components';
import { Input } from '../../../../components/ui/Input';

export const List = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  align-items: flex-start;
`;

export const Card = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  width: 100%;
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
`;

export const Line = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};
  align-items: center;

  > input:first-child {
    flex: 2;
    min-width: 140px;
  }

  select {
    width: auto;
  }
`;

export const Mono = styled(Input)`
  flex: 1;
  min-width: 120px;
  font-family: ${({ theme }) => theme.fonts.mono};
  font-variant-ligatures: none;
`;

export const Check = styled.label`
  display: inline-flex;
  align-items: center;
  gap: 6px;
`;

export const Muted = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;
