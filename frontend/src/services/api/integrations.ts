import { api, unwrap } from './client';
import type { components } from './schema';

export type Webhook = components['schemas']['WebhookOut'];
export type WebhookInput = components['schemas']['WebhookIn'];
export type WebhookDelivery = components['schemas']['WebhookDeliveryOut'];
export type PublicEvent = components['schemas']['PublicEventOut'];
export type ChatIntegration = components['schemas']['IntegrationOut'];
export type ChatIntegrationInput = components['schemas']['IntegrationIn'];
export type AutomationRule = components['schemas']['AutomationRuleOut'];
export type AutomationRuleInput = components['schemas']['AutomationRuleIn'];
export type AutomationRun = components['schemas']['AutomationRunOut'];
export type AutomationExample = components['schemas']['AutomationExampleOut'];
export type AutomationAction = components['schemas']['AutomationActionOut'];

export const integrationKeys = {
  events: ['admin', 'public-events'] as const,
  webhooks: ['admin', 'webhooks'] as const,
  deliveries: (id: string) => ['admin', 'webhooks', id, 'deliveries'] as const,
  chats: ['admin', 'integrations'] as const,
  rules: ['admin', 'automation', 'rules'] as const,
  runs: (id: string) => ['admin', 'automation', 'rules', id, 'runs'] as const,
  examples: ['admin', 'automation', 'examples'] as const,
  actions: ['admin', 'automation', 'actions'] as const,
};

const hook = (id: string) => ({ params: { path: { webhook_id: id } } });
const chat = (id: string) => ({ params: { path: { integration_id: id } } });
const rule = (id: string) => ({ params: { path: { rule_id: id } } });

export async function fetchPublicEvents() {
  return unwrap(await api.GET('/api/v1/webhooks/events'));
}

export async function fetchWebhooks() {
  return unwrap(await api.GET('/api/v1/webhooks'));
}

export async function createWebhook(body: WebhookInput) {
  return unwrap(await api.POST('/api/v1/webhooks', { body }));
}

export async function updateWebhook(id: string, body: WebhookInput) {
  return unwrap(await api.PUT('/api/v1/webhooks/{webhook_id}', { ...hook(id), body }));
}

export async function deleteWebhook(id: string) {
  unwrap(await api.DELETE('/api/v1/webhooks/{webhook_id}', hook(id)));
}

export async function pingWebhook(id: string) {
  return unwrap(await api.POST('/api/v1/webhooks/{webhook_id}/ping', hook(id)));
}

export async function rotateWebhookSecret(id: string) {
  return unwrap(await api.POST('/api/v1/webhooks/{webhook_id}/secret', hook(id))).secret;
}

export async function fetchDeliveries(id: string) {
  return unwrap(await api.GET('/api/v1/webhooks/{webhook_id}/deliveries', hook(id)));
}

export async function fetchChatIntegrations() {
  return unwrap(await api.GET('/api/v1/integrations'));
}

export async function createChatIntegration(body: ChatIntegrationInput) {
  return unwrap(await api.POST('/api/v1/integrations', { body }));
}

export async function updateChatIntegration(id: string, body: ChatIntegrationInput) {
  return unwrap(await api.PUT('/api/v1/integrations/{integration_id}', { ...chat(id), body }));
}

export async function deleteChatIntegration(id: string) {
  unwrap(await api.DELETE('/api/v1/integrations/{integration_id}', chat(id)));
}

export async function testChatIntegration(id: string, route: number) {
  return unwrap(
    await api.POST('/api/v1/integrations/{integration_id}/test', { ...chat(id), body: { route } }),
  );
}

export async function linkChatAccount(token: string) {
  return unwrap(await api.POST('/api/v1/integrations/link', { body: { token } }));
}

export async function fetchRules() {
  return unwrap(await api.GET('/api/v1/automation/rules'));
}

export async function createRule(body: AutomationRuleInput) {
  return unwrap(await api.POST('/api/v1/automation/rules', { body }));
}

export async function updateRule(id: string, body: AutomationRuleInput) {
  return unwrap(await api.PUT('/api/v1/automation/rules/{rule_id}', { ...rule(id), body }));
}

export async function deleteRule(id: string) {
  unwrap(await api.DELETE('/api/v1/automation/rules/{rule_id}', rule(id)));
}

export async function fetchRuns(id: string) {
  return unwrap(await api.GET('/api/v1/automation/rules/{rule_id}/runs', rule(id)));
}

export async function fetchExamples() {
  return unwrap(await api.GET('/api/v1/automation/examples'));
}

export async function fetchActions() {
  return unwrap(await api.GET('/api/v1/automation/actions'));
}
