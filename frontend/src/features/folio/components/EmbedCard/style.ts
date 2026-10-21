import styled from 'styled-components';

export const Frame = styled.div`
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  margin: ${({ theme }) => theme.space.lg} 0;
  border-radius: ${({ theme }) => theme.radius.lg};
  overflow: hidden;
  border: 1px solid ${({ theme }) => theme.color.border};
  background: ${({ theme }) => theme.color.surface2};

  iframe {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: 0;
  }
`;

export const Card = styled.a`
  display: flex;
  gap: ${({ theme }) => theme.space.lg};
  margin: ${({ theme }) => theme.space.lg} 0;
  padding: ${({ theme }) => theme.space.lg};
  color: ${({ theme }) => theme.color.text};
  text-decoration: none;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface};

  &:hover {
    border-color: ${({ theme }) => theme.color.accent};
  }
`;

export const Text = styled.span`
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
`;

export const Title = styled.span`
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

export const Description = styled.span`
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
`;

export const Site = styled.span`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Image = styled.img`
  width: 120px;
  height: 80px;
  object-fit: cover;
  border-radius: ${({ theme }) => theme.radius.md};
  flex-shrink: 0;
`;

export const Hidden = styled.span`
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
`;
