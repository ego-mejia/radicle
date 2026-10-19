import styled from 'styled-components';
import { Input } from '../../../../../../components/ui/Input';

export const Form = styled.form`
  display: contents;
`;

export const Pair = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: ${({ theme }) => theme.space.md};

  @media (max-width: 520px) {
    grid-template-columns: 1fr;
  }
`;

export const Mono = styled(Input)`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-variant-ligatures: none;
`;

export const Options = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  align-items: flex-start;
`;

export const OptionRow = styled.div`
  display: grid;
  grid-template-columns: 28px 1fr 1fr 32px;
  gap: ${({ theme }) => theme.space.sm};
  align-items: center;
  width: 100%;
`;

export const Swatch = styled.input`
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.sm};
  background: none;
  cursor: pointer;
`;

export const Checks = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.md};

  label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
  }
`;
