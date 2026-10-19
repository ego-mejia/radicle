import type { components } from './schema';

type S = components['schemas'];

export type Me = S['MeOut'];
export type MeProject = S['MeProject'];
export type User = S['UserOut'];
export type UserRef = S['UserRef'];
export type Token = S['TokenOut'];
export type TokenCreated = S['TokenCreated'];
export type AgentCreated = S['AgentCreated'];
export type Project = S['ProjectOut'];
export type ProjectDetail = S['ProjectDetail'];
export type ProjectRole = Project['role'];
export type Area = S['AreaOut'];
export type Milestone = S['MilestoneOut'];
export type Member = S['MemberOut'];
export type Workflow = S['WorkflowOut'];
export type Ticket = S['TicketOut'];
export type TicketSummary = S['TicketSummary'];
export type TicketCreate = S['TicketCreate'];
export type TicketPatch = S['TicketPatch'];
export type TicketType = Ticket['type'];
export type Priority = Ticket['priority'];
export type Resolution = NonNullable<Ticket['resolution']>;
export type Category = Ticket['status']['category'];
export type ChecklistItem = S['ChecklistItemOut'];
export type Link = S['LinkOut'];
export type TransitionOption = S['TransitionOption'];
export type Comment = S['CommentOut'];
export type HistoryEvent = S['EventOut'];
export type SearchPage = S['SearchPage'];
export type SearchFields = S['SearchFields'];
export type TicketWarning = S['WarningOut'];

export const TICKET_TYPES: TicketType[] = ['task', 'bug', 'draft'];
export const PRIORITIES: Priority[] = ['highest', 'high', 'medium', 'low', 'lowest'];
export const CATEGORIES: Category[] = ['todo', 'in_progress', 'done'];
export const LINK_TYPES = ['blocks', 'relates_to', 'duplicates', 'clones'] as const;

export type CustomField = S['CustomFieldOut'];
export type CustomFieldType = CustomField['field_type'];
export type CustomFieldCreate = S['CustomFieldCreate'];
export type CustomFieldPatch = S['CustomFieldPatch'];
export const CUSTOM_FIELD_TYPES: CustomFieldType[] = [
  'text',
  'number',
  'date',
  'select',
  'checkbox',
  'user',
  'url',
];

export type Template = S['TemplateOut'];
export type TemplateDetail = S['TemplateDetail'];
export type TemplateConfig = S['TemplateConfig'];
export type WorkflowConf = S['WorkflowConf'];
export type StatusConf = S['StatusConf'];
export type TransitionConf = S['TransitionConf'];
export type FieldConf = S['FieldConf'];
export type SyncRun = S['SyncRunOut'];
export type BlockedPolicy = ProjectDetail['blocked_policy'];
export const RESOLUTIONS: Resolution[] = ['done', 'wont_do', 'duplicate', 'cannot_reproduce'];

export type FormSchema = S['FormSchemaOut'];
export type SchemaField = S['SchemaFieldOut'];
export type ScreenOperation = FormSchema['operation'];
export type Screen = S['ScreenOut'];
export type ScreenIn = S['ScreenIn'];

export type Attachment = S['AttachmentOut'];
export type Limits = S['Limits'];
export type ImagePreset = 'original' | 'large' | 'medium' | 'small';

export type Worklog = S['WorklogOut'];
