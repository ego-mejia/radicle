import type { CustomField, Ticket } from '../services/api/types';

/** Whether a custom field shows on a ticket: active, and matching its type and area. */
export function appliesTo(field: CustomField, ticket: Pick<Ticket, 'type' | 'area'>): boolean {
  if (field.archived || !field.applies_to_types.includes(ticket.type)) return false;
  return field.applies_to_areas === null || field.applies_to_areas.includes(ticket.area ?? '');
}
