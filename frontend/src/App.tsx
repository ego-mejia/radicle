import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { ThemeModeProvider } from './contexts/ThemeModeContext';
import { StatusPage } from './pages/StatusPage';

export function App() {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeModeProvider>
        <StatusPage />
      </ThemeModeProvider>
    </QueryClientProvider>
  );
}
