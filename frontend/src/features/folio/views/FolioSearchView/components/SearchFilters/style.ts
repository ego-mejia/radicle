import styled from 'styled-components';

export const Filters = styled.fieldset`
  margin: 0;
  padding: 0;
  border: 0;
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.md};

  > * {
    flex: 1 1 160px;
    min-width: 0;
  }
`;

export const Legend = styled.legend`
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
`;
