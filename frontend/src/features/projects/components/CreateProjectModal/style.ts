import styled from 'styled-components';
import { Input } from '../../../../components/ui/Input';

export const Form = styled.form`
  display: contents;
`;

export const KeyInput = styled(Input)`
  font-family: ${({ theme }) => theme.fonts.mono};
  text-transform: uppercase;
`;

export const Modes = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};

  label {
    display: flex;
    gap: ${({ theme }) => theme.space.sm};
    align-items: flex-start;
    cursor: pointer;
  }

  span {
    display: flex;
    flex-direction: column;
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;
