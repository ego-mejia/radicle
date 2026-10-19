import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import { ThemeModeProvider } from '../contexts/ThemeModeContext';

export function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeModeProvider>{ui}</ThemeModeProvider>
    </QueryClientProvider>,
  );
}
