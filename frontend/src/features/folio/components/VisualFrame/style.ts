import styled from 'styled-components';

export const Figure = styled.figure`
  margin: 0;
`;

export const Frame = styled.iframe`
  display: block;
  width: 100%;
  border: 0;
  background: transparent;
`;

export const Caption = styled.figcaption`
  margin-top: ${({ theme }) => theme.space.xs};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  text-align: center;
`;

// Screen readers read it with the frame; on screen the visual speaks for itself.
export const Description = styled.p`
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
`;
