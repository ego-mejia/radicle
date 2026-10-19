import type { SchemaField } from '../services/api/types';

export type Values = Record<string, unknown>;

export function isEmpty(value: unknown): boolean {
  return (
    value === undefined || value === null || value === '' || (Array.isArray(value) && !value.length)
  );
}

/** Fields of a schema the form does not lay out by hand (title and description are). */
export function visibleFields(fields: SchemaField[], area?: string | null): SchemaField[] {
  return fields.filter(
    (f) =>
      f.field !== 'title' &&
      f.field !== 'description_md' &&
      (!f.areas || (area ? f.areas.includes(area) : false)),
  );
}

/** Required fields without a value, for client-side checks before sending. */
export function missingRequired(fields: SchemaField[], values: Values, area?: string | null) {
  return [...fields.filter((f) => f.field === 'title'), ...visibleFields(fields, area)].filter(
    (f) => f.required && isEmpty(values[f.field]),
  );
}

/** Split form values into the API body: fixed fields and custom_fields. */
export function toBody(values: Values): { body: Record<string, unknown>; custom: Values } {
  const body: Record<string, unknown> = {};
  const custom: Values = {};
  for (const [name, value] of Object.entries(values)) {
    if (isEmpty(value)) continue;
    if (name.startsWith('cf.')) custom[name.slice(3)] = value;
    else body[name] = value;
  }
  return { body, custom };
}
