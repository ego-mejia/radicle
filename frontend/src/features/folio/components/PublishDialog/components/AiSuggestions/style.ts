import styled from 'styled-components';

export const Box = styled.div`
  display: grid;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => theme.space.md};
  border: 1px dashed ${({ theme }) => theme.color.accent};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => theme.color.text};

  &[role='status'] {
    display: flex;
    align-items: center;
    color: ${({ theme }) => theme.color.textMuted};
  }

  svg {
    width: 16px;
    height: 16px;
  }
`;

export const Title = styled.h3`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Row = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.md};
`;

export const Label = styled.div`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Text = styled.div`
  font-size: ${({ theme }) => theme.fontSize.md};
`;
