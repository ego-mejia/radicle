import * as Dialog from '@radix-ui/react-dialog';
import styled, { keyframes } from 'styled-components';

const fadeIn = keyframes`from { opacity: 0 } to { opacity: 1 }`;
const rise = keyframes`from { opacity: 0; transform: translate(-50%, -48%) } to { opacity: 1; transform: translate(-50%, -50%) }`;
const slide = keyframes`from { transform: translateX(16px); opacity: 0 } to { transform: none; opacity: 1 }`;

export const Overlay = styled(Dialog.Overlay)`
  position: fixed;
  inset: 0;
  background: rgba(10, 12, 14, 0.45);
  animation: ${fadeIn} 0.12s ease-out;
  z-index: 40;
`;

export const Content = styled(Dialog.Content)<{ $width: number }>`
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: min(${({ $width }) => $width}px, calc(100vw - 32px));
  max-height: calc(100vh - 48px);
  overflow: auto;
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
  animation: ${rise} 0.14s ease-out;
  z-index: 41;

  &:focus {
    outline: none;
  }
`;

export const Panel = styled(Dialog.Content)`
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: min(760px, 100vw);
  overflow: auto;
  background: ${({ theme }) => theme.color.bg};
  border-left: 1px solid ${({ theme }) => theme.color.border};
  box-shadow: -16px 0 40px rgba(0, 0, 0, 0.18);
  animation: ${slide} 0.16s ease-out;
  z-index: 41;

  &:focus {
    outline: none;
  }
`;

export const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => `${theme.space.lg} ${theme.space.xl}`};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
`;

export const Title = styled(Dialog.Title)`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.lg};
  font-weight: 700;
`;

export const Body = styled.div`
  padding: ${({ theme }) => theme.space.xl};
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Footer = styled.div`
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => `${theme.space.md} ${theme.space.xl}`};
  border-top: 1px solid ${({ theme }) => theme.color.border};
`;

export const HiddenTitle = styled(Dialog.Title)`
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
`;
