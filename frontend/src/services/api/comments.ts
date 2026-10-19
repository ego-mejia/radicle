import { api, unwrap } from './client';

export async function fetchComments(key: string) {
  return unwrap(
    await api.GET('/api/v1/tickets/{key}/comments', {
      params: { path: { key }, query: { limit: 200, order: 'asc' } },
    }),
  ).items;
}

export async function addComment(key: string, body: string) {
  return unwrap(
    await api.POST('/api/v1/tickets/{key}/comments', {
      params: { path: { key } },
      body: { body_md: body },
    }),
  );
}

export async function editComment(id: string, body: string) {
  return unwrap(
    await api.PATCH('/api/v1/comments/{comment_id}', {
      params: { path: { comment_id: id } },
      body: { body_md: body },
    }),
  );
}

export async function deleteComment(id: string) {
  unwrap(
    await api.DELETE('/api/v1/comments/{comment_id}', { params: { path: { comment_id: id } } }),
  );
}

export async function setReaction(id: string, emoji: string, on: boolean) {
  const params = { params: { path: { comment_id: id, emoji } } };
  return unwrap(
    on
      ? await api.PUT('/api/v1/comments/{comment_id}/reactions/{emoji}', params)
      : await api.DELETE('/api/v1/comments/{comment_id}/reactions/{emoji}', params),
  );
}
