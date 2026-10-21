import { api, unwrap } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type AiAvailability = S['AiAvailabilityOut'];
export type RewriteMode = S['RewriteIn']['mode'];
export type MetadataSuggestion = S['MetadataSuggestionOut'];
export type GlossaryTerm = S['GlossaryTermOut'];
export type GlossaryStatus = GlossaryTerm['status'];
export type GlossaryTermIn = S['GlossaryTermIn'];
export type GlossaryTermPatch = S['GlossaryTermPatch'];

/** Query keys for Folio's AI and glossary (Folio 4.6). */
export const aiKeys = {
  availability: (space: string) => ['folio', 'ai', space] as const,
  glossary: (status: GlossaryStatus) => ['folio', 'glossary', status] as const,
};

export async function fetchAiAvailability(space: string): Promise<AiAvailability> {
  return unwrap(await api.GET('/api/v1/folio/ai/availability', { params: { query: { space } } }));
}

export async function summarizePage(nodeId: string): Promise<string> {
  const out = unwrap(await api.POST('/api/v1/folio/ai/summarize', { body: { node_id: nodeId } }));
  return out.summary;
}

export async function rewriteText(
  nodeId: string,
  text: string,
  mode: RewriteMode,
  language?: string,
): Promise<string> {
  const body = { node_id: nodeId, text, mode, language: language || null };
  return unwrap(await api.POST('/api/v1/folio/ai/rewrite', { body })).text;
}

export async function suggestMetadata(nodeId: string): Promise<MetadataSuggestion> {
  return unwrap(await api.POST('/api/v1/folio/ai/suggest-metadata', { body: { node_id: nodeId } }));
}

export async function fetchGlossary(status: GlossaryStatus = 'approved'): Promise<GlossaryTerm[]> {
  const query = status === 'approved' ? {} : { status };
  return unwrap(await api.GET('/api/v1/folio/glossary', { params: { query } })).items;
}

export async function createGlossaryTerm(body: GlossaryTermIn): Promise<GlossaryTerm> {
  return unwrap(await api.POST('/api/v1/folio/glossary', { body }));
}

export async function patchGlossaryTerm(
  id: string,
  body: GlossaryTermPatch,
): Promise<GlossaryTerm> {
  return unwrap(
    await api.PATCH('/api/v1/folio/glossary/{term_id}', {
      params: { path: { term_id: id } },
      body,
    }),
  );
}

export async function suggestGlossaryTerms(): Promise<GlossaryTerm[]> {
  return unwrap(await api.POST('/api/v1/folio/glossary/suggestions')).items;
}
