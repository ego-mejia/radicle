import createClient, { type Middleware } from 'openapi-fetch';
import type { paths } from './schema';

const CSRF_COOKIE = 'radicle_csrf';
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

function readCookie(name: string): string | null {
  const match = document.cookie.split('; ').find((part) => part.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

// Cookie sessions need the CSRF token echoed back on every mutation.
const csrf: Middleware = {
  onRequest({ request }) {
    if (!SAFE_METHODS.has(request.method)) {
      const token = readCookie(CSRF_COOKIE);
      if (token) request.headers.set('X-CSRF-Token', token);
    }
    return request;
  },
};

export const api = createClient<paths>({
  baseUrl: window.location.origin,
  credentials: 'same-origin',
  // Resolve fetch per call so tests (and polyfills) can replace it after import.
  fetch: (request) => globalThis.fetch(request),
});
api.use(csrf);

/** RFC 9457 problem returned by every API error. */
export type Problem = {
  type: string;
  title: string;
  status: number;
  detail: string;
  errors: { field?: string; message: string }[];
};

export class ApiError extends Error {
  constructor(public readonly problem: Problem) {
    super(problem.detail);
  }
}

/** Unwraps an openapi-fetch result, throwing ApiError on problem responses. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined || !result.response.ok) {
    const problem = (result.error as Problem | undefined) ?? {
      type: 'about:blank',
      title: result.response.statusText,
      status: result.response.status,
      detail: result.response.statusText,
      errors: [],
    };
    throw new ApiError(problem);
  }
  return result.data as T;
}
