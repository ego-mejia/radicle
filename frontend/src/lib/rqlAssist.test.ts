import { describe, expect, it } from 'vitest';
import type { SearchFields } from '../services/api/types';
import { suggest } from './rqlAssist';

const META: SearchFields = {
  fields: [],
  sort_fields: [],
  functions: [],
  keywords: [],
  values: {
    project: 'PA',
    statuses: [],
    areas: [],
    milestones: [],
    handles: ['luis'],
    tags: [],
    custom_fields: [
      {
        name: 'cf.environment',
        type: 'select',
        operators: ['=', '!='],
        supports_in: true,
        supports_empty: true,
        description: 'Environment',
        values: ['prod', 'dev'],
      },
      {
        name: 'cf.owner',
        type: 'user',
        operators: ['=', '!='],
        supports_in: true,
        supports_empty: true,
        description: 'Owner',
        values: [],
      },
    ],
  },
};

describe('suggest with custom fields', () => {
  it('suggests cf fields, their operators and option values', () => {
    expect(suggest('cf.e', META).items.map((s) => s.label)).toEqual(['cf.environment']);
    expect(suggest('cf.environment ', META).items.map((s) => s.label)).toContain('IN');
    expect(suggest('cf.environment = ', META).items.map((s) => s.label)).toEqual(['prod', 'dev']);
    expect(suggest('cf.owner = ', META).items.map((s) => s.label)).toEqual([
      'currentUser()',
      'luis',
    ]);
  });
});
