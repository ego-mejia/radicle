import styled from 'styled-components';

export const Show = styled.button`
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 28px;
  padding: 0;
  font: inherit;
  color: inherit;
  text-align: left;
  background: none;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.sm};
  cursor: text;

  &:hover,
  &:focus-visible {
    background: ${({ theme }) => theme.color.surface2};
  }
`;

export const Choices = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};

  label {
    display: inline-flex;
    align-items: center;
    gap: ${({ theme }) => theme.space.xs};
  }

  button {
    font: inherit;
    color: ${({ theme }) => theme.color.accent};
    background: none;
    border: 0;
    cursor: pointer;
  }
`;
