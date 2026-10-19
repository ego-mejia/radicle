import styled from 'styled-components';

export const Upload = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Bar = styled.div`
  flex: 1;
  height: 6px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface2};
  overflow: hidden;

  span {
    display: block;
    height: 100%;
    background: ${({ theme }) => theme.color.accentFill};
    transition: width 0.15s;
  }
`;

export const Presets = styled.div`
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
