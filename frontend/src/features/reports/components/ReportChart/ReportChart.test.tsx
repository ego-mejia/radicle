import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import i18n from '../../../../i18n';
import type { ReportData } from '../../../../services/api/types';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { ReportChart } from '.';

describe('ReportChart', () => {
  beforeEach(() => i18n.changeLanguage('en'));

  it('shows milestone progress with the at-risk forecast', async () => {
    const report: ReportData = {
      type: 'milestone_progress',
      title: 'Progress · V1',
      columns: ['metric', 'value'],
      rows: [],
      summary: {
        percent_by_count: 50,
        percent_by_hours: 40,
        remaining_hours: 7,
        throughput_hours_per_week: 2,
        target_date: '2026-10-01',
        forecast_date: '2026-10-13',
        state: 'at_risk',
      },
    };
    renderWithProviders(<ReportChart report={report} />);
    expect(await screen.findByText('At risk')).toBeInTheDocument();
    expect(screen.getByText('40%')).toBeInTheDocument();
    expect(screen.getByText('2 h/week')).toBeInTheDocument();
  });

  it('shows the sprint outcome counts', async () => {
    const report: ReportData = {
      type: 'sprint',
      title: 'Sprint report',
      columns: [],
      rows: [],
      summary: {
        committed_hours: 16,
        completed_hours: 8,
        goal_met: true,
        counts: { completed: 2, not_completed: 2, added_after_start: 1, removed: 0 },
      },
    };
    renderWithProviders(<ReportChart report={report} />);
    expect(await screen.findByText('Added after start')).toBeInTheDocument();
    expect(screen.getByText('16h')).toBeInTheDocument();
    expect(screen.getByText('Yes')).toBeInTheDocument();
  });
});
