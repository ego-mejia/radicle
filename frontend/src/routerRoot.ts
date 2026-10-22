import { createRootRouteWithContext, Outlet } from '@tanstack/react-router';
import type { QueryClient } from '@tanstack/react-query';

export type RouterContext = { queryClient: QueryClient };

/** A non-empty string search param, or undefined. */
export const str = (value: unknown) => (typeof value === 'string' && value ? value : undefined);

export const rootRoute = createRootRouteWithContext<RouterContext>()({ component: Outlet });
