import styled from 'styled-components';

export const Card = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  padding: ${({ theme }) => theme.space.xl};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.lg};
  }

  p.help {
    margin: -8px 0 0;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Rows = styled.div`
  display: flex;
  flex-direction: column;
`;

export const Row = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  min-height: 42px;
  padding: 6px 0;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};

  &:last-child {
    border-bottom: 0;
  }

  select {
    width: auto;
  }
`;

export const Grow = styled.div`
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Inline = styled.form`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
  flex-wrap: wrap;
  align-items: flex-end;

  > div:first-child {
    flex: 1;
    min-width: 160px;
  }

  select {
    width: auto;
  }
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

export const Actions = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
  flex-wrap: wrap;
`;

export const Muted = styled.small`
  color: ${({ theme }) => theme.color.textMuted};
`;
