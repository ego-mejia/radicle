import { ApiError, CSRF_COOKIE, api, readCookie, unwrap } from './client';
import type { Attachment, ImagePreset } from './types';

export const attachmentKeys = {
  limits: ['limits'] as const,
};

export async function fetchLimits() {
  return unwrap(await api.GET('/api/v1/limits'));
}

/** Upload with progress (fetch cannot report upload progress, so this uses XHR). */
export function uploadAttachment(
  ticketKey: string,
  file: File,
  options: { resize?: ImagePreset; commentId?: string } = {},
  onProgress?: (fraction: number) => void,
): Promise<Attachment> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append('file', file, file.name);
    if (options.resize) form.append('resize', options.resize);
    if (options.commentId) form.append('comment_id', options.commentId);
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `/api/v1/tickets/${encodeURIComponent(ticketKey)}/attachments`);
    xhr.withCredentials = true;
    const token = readCookie(CSRF_COOKIE);
    if (token) xhr.setRequestHeader('X-CSRF-Token', token);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress?.(e.loaded / e.total);
    xhr.onload = () => {
      let body: unknown = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        body = null;
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as Attachment);
      else
        reject(
          new ApiError({
            type: 'about:blank',
            title: 'Upload failed',
            status: xhr.status,
            detail: (body as { detail?: string } | null)?.detail ?? `Upload failed (${xhr.status})`,
            errors: [],
          }),
        );
    };
    xhr.onerror = () =>
      reject(
        new ApiError({
          type: 'about:blank',
          title: 'Network error',
          status: 0,
          detail: 'The upload could not reach the server.',
          errors: [],
        }),
      );
    xhr.send(form);
  });
}

export async function resizeAttachment(id: string, preset: ImagePreset) {
  return unwrap(
    await api.POST('/api/v1/attachments/{attachment_id}/resize', {
      params: { path: { attachment_id: id } },
      body: { preset },
    }),
  );
}

export async function deleteAttachment(id: string) {
  unwrap(
    await api.DELETE('/api/v1/attachments/{attachment_id}', {
      params: { path: { attachment_id: id } },
    }),
  );
}

/** URL the browser can load with the session cookie, for `attachment:<id>` in markdown. */
export function attachmentSrc(id: string, variant: 'original' | 'preview' | 'thumb' = 'original') {
  return `/api/v1/attachments/${id}/content?variant=${variant}`;
}
