// Shared test data for the calendar components.

import type { CalendarAgenda, FolioCalendar } from '../../../services/api/folioCalendars';

export const CAL_ID = '5d2f8a17-3c4b-4e6a-9f1d-2b7c8e9a0f13';

export const CALENDAR: FolioCalendar = {
  id: CAL_ID,
  space: 'eng',
  name: 'Releases',
  color: 'green',
  docket_projects: ['PA'],
  ical_path: '/ical/tok.ics',
  can_manage: true,
  can_add: true,
  created_at: '2026-10-21T10:00:00Z',
};

export const AGENDA: CalendarAgenda = {
  events: [
    {
      id: 'e1',
      title: 'Release 2.0',
      description: '',
      start_at: new Date(2026, 11, 10, 15).toISOString(),
      end_at: new Date(2026, 11, 10, 16).toISOString(),
      all_day: false,
      category: 'release',
      people: ['luis'],
      created_by: 'ana',
      can_edit: true,
    },
    {
      id: 'e2',
      title: 'Vacaciones de Ana',
      description: '',
      start_at: '2026-12-14T00:00:00Z',
      end_at: '2026-12-16T00:00:00Z',
      all_day: true,
      category: 'vacation',
      people: [],
      created_by: 'ana',
      can_edit: false,
    },
  ],
  milestones: [{ project: 'PA', name: 'V1', status: 'open', due: '2026-12-15' }],
};
