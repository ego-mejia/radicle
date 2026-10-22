import styled from 'styled-components';

export const Item = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  padding-bottom: ${({ theme }) => theme.space.sm};
`;

export const Urls = styled.div`
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: ${({ theme }) => theme.space.xs} ${({ theme }) => theme.space.sm};
  padding-left: ${({ theme }) => theme.space.xl};
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};

  code {
    color: ${({ theme }) => theme.color.text};
    word-break: break-all;
  }
`;

export const Channel = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
  align-items: center;
  padding-left: ${({ theme }) => theme.space.xl};
  font-size: ${({ theme }) => theme.fontSize.sm};

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;
