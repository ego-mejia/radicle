export type RuleKind = 'condition' | 'validator' | 'post_function';
export type RuleParam = 'roles' | 'kind' | 'field' | 'value' | 'tag' | 'template';

/** Mirror of the backend catalog (services/rule_catalog.py). */
export const RULE_CATALOG: Record<string, { kind: RuleKind; params: RuleParam[] }> = {
  only_assignee: { kind: 'condition', params: [] },
  only_reporter: { kind: 'condition', params: [] },
  only_roles: { kind: 'condition', params: ['roles'] },
  only_user_kind: { kind: 'condition', params: ['kind'] },
  not_blocked: { kind: 'condition', params: [] },
  checklist_complete: { kind: 'validator', params: [] },
  field_required: { kind: 'validator', params: ['field'] },
  has_estimate: { kind: 'validator', params: [] },
  children_done: { kind: 'validator', params: [] },
  has_worklog: { kind: 'validator', params: [] },
  comment_required: { kind: 'validator', params: [] },
  assign_to_actor: { kind: 'post_function', params: [] },
  unassign: { kind: 'post_function', params: [] },
  set_field: { kind: 'post_function', params: ['field', 'value'] },
  clear_field: { kind: 'post_function', params: ['field'] },
  add_tag: { kind: 'post_function', params: ['tag'] },
  remove_tag: { kind: 'post_function', params: ['tag'] },
  add_comment: { kind: 'post_function', params: ['template'] },
};

export const RULE_KINDS: RuleKind[] = ['condition', 'validator', 'post_function'];

export const RULE_FIELDS = [
  'priority',
  'area',
  'milestone',
  'assignee',
  'due_date',
  'estimate_hours',
  'description_md',
  'parent',
];

export function defaultConfig(ruleType: string): Record<string, unknown> {
  const params = RULE_CATALOG[ruleType]?.params ?? [];
  const config: Record<string, unknown> = {};
  if (params.includes('roles')) config.roles = ['admin'];
  if (params.includes('kind')) config.kind = 'human';
  if (params.includes('field')) config.field = 'assignee';
  if (params.includes('value')) config.value = '';
  if (params.includes('tag')) config.tag = '';
  if (params.includes('template')) config.template = '{actor}: {from} → {to}';
  return config;
}
