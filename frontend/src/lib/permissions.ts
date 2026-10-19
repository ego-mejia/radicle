/** What the current user may do in a project, from the permissions the API sends. */
export type Permission =
  | 'ticket.create'
  | 'ticket.edit'
  | 'ticket.transition'
  | 'ticket.delete'
  | 'ticket.move'
  | 'ticket.bulk_edit'
  | 'ticket.set_security'
  | 'comment.create'
  | 'comment.delete_any'
  | 'attachment.upload'
  | 'attachment.delete_any'
  | 'worklog.create'
  | 'worklog.edit_any'
  | 'vote'
  | 'link.manage'
  | 'sprint.manage'
  | 'board.manage'
  | 'inbox.triage'
  | 'project.settings'
  | 'members.manage';

type WithPermissions = { permissions?: string[]; archived?: boolean } | null | undefined;

/** False for archived projects: they are read-only whatever the matrix says. */
export function can(project: WithPermissions, permission: Permission): boolean {
  if (!project || project.archived) return false;
  return (project.permissions ?? []).includes(permission);
}
