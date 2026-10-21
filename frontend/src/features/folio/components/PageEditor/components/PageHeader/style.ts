import styled from 'styled-components';

export const Header = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  margin-bottom: ${({ theme }) => theme.space.xl};
`;

export const Tools = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Icon = styled.button`
  font-size: 44px;
  line-height: 1;
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
  align-self: flex-start;
`;

export const Title = styled.textarea`
  width: 100%;
  border: 0;
  resize: none;
  background: transparent;
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  font-size: 40px;
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.025em;
  outline: none;
  field-sizing: content;
  &::placeholder {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;
