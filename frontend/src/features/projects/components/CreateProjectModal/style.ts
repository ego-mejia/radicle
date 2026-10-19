import styled from 'styled-components';
import { Input } from '../../../../components/ui/Input';

export const Form = styled.form`
  display: contents;
`;

export const KeyInput = styled(Input)`
  font-family: ${({ theme }) => theme.fonts.mono};
  text-transform: uppercase;
`;
