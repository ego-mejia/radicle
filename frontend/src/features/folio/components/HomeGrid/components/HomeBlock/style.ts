import styled from 'styled-components';

export { Heading } from '../DocList/style';

export const Text = styled.section`
  box-sizing: border-box;
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  padding: ${({ theme }) => theme.space.xl};
  overflow: auto;
`;
