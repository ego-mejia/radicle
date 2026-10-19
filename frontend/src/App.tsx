import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from '@tanstack/react-router';
import { useState } from 'react';
import { ThemeModeProvider } from './contexts/ThemeModeContext';
import { ToastProvider } from './contexts/ToastProvider';
import { createAppRouter } from './router';
import { isApiError } from './services/api/client';

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 15_000,
        retry: (count, error) => !isApiError(error) && count < 2,
        refetchOnWindowFocus: true,
      },
    },
  });
}

export function App() {
  const [queryClient] = useState(makeQueryClient);
  const [router] = useState(() => createAppRouter(queryClient));
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeModeProvider>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </ThemeModeProvider>
    </QueryClientProvider>
  );
}
