import styled from 'styled-components';
import { Button } from '../../../../../../components/ui/Button';

export const Checks = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.md};

  label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
`;

export const Danger = styled(Button)`
  margin-right: auto;
  color: ${({ theme }) => theme.color.danger};
`;
