import { ChevronDown, ChevronRight } from 'lucide-react';
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'styled-components';
import { TypeIcon } from '../../../../components/icons/TypeIcon';
import {
  arrowPath,
  dayRange,
  DRAG_TYPE,
  flatten,
  PX_PER_DAY,
  spanOf,
  ticks as makeTicks,
  toDay,
  toIso,
  visibleRange,
  type Zoom,
} from '../../../../lib/timeline';
import type { Timeline, TimelineTicket } from '../../../../services/api/types';
import { ChartHeader } from './components/ChartHeader';
import { TicketBar } from './components/TicketBar';
import * as S from './style';

const ROW = 30;
const HEADER = 40;

type Props = {
  data: Timeline;
  zoom: Zoom;
  today: string;
  canEdit: boolean;
  collapsed: Set<string>;
  onToggle: (group: string) => void;
  onOpen: (key: string) => void;
  onChange: (
    ticket: TimelineTicket,
    dates: { start_date: string | null; due_date: string | null },
  ) => void;
  onDropUndated: (key: string, day: string) => void;
};

/** Hand-made Gantt: virtualized rows, bars by category, milestones, today and Blocks arrows. */
export function TimelineChart({
  data,
  zoom,
  today,
  canEdit,
  collapsed,
  onToggle,
  onOpen,
  onChange,
  onDropUndated,
}: Props) {
  const { t, i18n } = useTranslation();
  const theme = useTheme();
  const chartRef = useRef<HTMLDivElement>(null);
  const labelsRef = useRef<HTMLDivElement>(null);
  const [view, setView] = useState({ top: 0, height: 600 });
  const px = PX_PER_DAY[zoom];
  const rows = useMemo(() => flatten(data.groups, collapsed), [data.groups, collapsed]);
  const dates = useMemo(
    () =>
      data.groups.flatMap((g) => [
        g.milestone?.target_date,
        g.milestone?.forecast_date,
        ...g.tickets.flatMap((tk) => [tk.start_date, tk.due_date]),
      ]),
    [data.groups],
  );
  const [first, last] = dayRange(dates, today);
  const width = (last - first + 1) * px;
  const height = Math.max(rows.length * ROW, 120);
  const tickList = useMemo(
    () => makeTicks(first, last, zoom, i18n.language),
    [first, last, zoom, i18n.language],
  );
  const [from, to] = visibleRange(view.top, view.height, ROW, rows.length);
  const index = new Map(rows.map((r, i) => [r.key, i]));
  const todayX = (toDay(today) - first) * px;

  useLayoutEffect(() => {
    const el = chartRef.current;
    if (el) el.scrollLeft = Math.max(0, todayX - el.clientWidth / 3);
    // Only when the zoom changes: keep the user's position otherwise.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zoom]);
  useEffect(() => {
    const el = chartRef.current;
    if (!el) return;
    const resize = () => setView((v) => ({ ...v, height: el.clientHeight }));
    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  const onScroll = () => {
    const el = chartRef.current;
    if (!el) return;
    if (labelsRef.current) labelsRef.current.scrollTop = el.scrollTop;
    setView({ top: el.scrollTop, height: el.clientHeight });
  };
  const dayAt = (clientX: number, target: Element) => {
    const rect = target.getBoundingClientRect();
    return toIso(first + Math.floor((clientX - rect.left) / px));
  };

  const xOf = (iso: string) => (toDay(iso) - first) * px;
  const visible = rows.slice(from, to);

  return (
    <S.Wrapper>
      <S.Labels ref={labelsRef}>
        <S.LabelsHead style={{ height: HEADER }}>{t('timeline.ticket')}</S.LabelsHead>
        <div style={{ height, position: 'relative' }}>
          {visible.map((row, i) => {
            const top = (from + i) * ROW;
            if (row.kind === 'group') {
              return (
                <S.GroupLabel
                  key={`g-${row.key}`}
                  style={{ top, height: ROW }}
                  type="button"
                  aria-expanded={!row.collapsed}
                  onClick={() => onToggle(row.key)}
                >
                  {row.collapsed ? <ChevronRight /> : <ChevronDown />}
                  <span>{row.label || t('timeline.noGroup')}</span>
                  <small>{row.count}</small>
                </S.GroupLabel>
              );
            }
            return (
              <S.TicketLabel
                key={row.key}
                style={{ top, height: ROW }}
                type="button"
                onClick={() => onOpen(row.key)}
                title={row.ticket.title}
              >
                <TypeIcon type={row.ticket.type} size={13} />
                <b>{row.key}</b>
                <span>{row.ticket.title}</span>
              </S.TicketLabel>
            );
          })}
        </div>
      </S.Labels>
      <S.Chart ref={chartRef} onScroll={onScroll} data-testid="timeline-chart">
        <S.Sticky style={{ width }}>
          <ChartHeader ticks={tickList} origin={first} px={px} width={width} height={HEADER} />
        </S.Sticky>
        <svg
          width={width}
          height={height}
          role="group"
          aria-label={t('timeline.chart')}
          onDragOver={(e) =>
            canEdit && e.dataTransfer.types.includes(DRAG_TYPE) && e.preventDefault()
          }
          onDrop={(e) => {
            const key = e.dataTransfer.getData(DRAG_TYPE);
            if (key) onDropUndated(key, dayAt(e.clientX, e.currentTarget));
          }}
        >
          {visible.map((row, i) =>
            row.kind === 'group' ? (
              <rect
                key={`bg-${row.key}`}
                x={0}
                y={(from + i) * ROW}
                width={width}
                height={ROW}
                fill={theme.color.surface2}
              />
            ) : null,
          )}
          {tickList
            .filter((tick) => tick.major)
            .map((tick) => (
              <line
                key={tick.day}
                x1={(tick.day - first) * px}
                x2={(tick.day - first) * px}
                y1={0}
                y2={height}
                stroke={theme.color.border}
                strokeWidth={0.5}
              />
            ))}
          {data.groups.map((g) => {
            const m = g.milestone;
            const y = (index.get(g.key) ?? -1) * ROW;
            if (!m?.target_date) return null;
            const x = xOf(m.target_date) + px / 2;
            return (
              <g key={`m-${g.key}`} data-testid={`milestone-${m.name}`}>
                <line
                  x1={x}
                  x2={x}
                  y1={0}
                  y2={height}
                  stroke={theme.color.textMuted}
                  strokeDasharray="4 4"
                />
                {y >= 0 && (
                  <path
                    d={`M${x},${y + 7} l8,8 l-8,8 l-8,-8 z`}
                    fill={theme.color.accent}
                    aria-label={t('timeline.target', { name: m.name, date: m.target_date })}
                  >
                    <title>{t('timeline.target', { name: m.name, date: m.target_date })}</title>
                  </path>
                )}
                {y >= 0 && m.forecast_date && (
                  <g>
                    <title>{t(`timeline.forecast.${m.state}`, { date: m.forecast_date })}</title>
                    <circle
                      cx={xOf(m.forecast_date) + px / 2}
                      cy={y + ROW / 2}
                      r={5}
                      fill="none"
                      strokeWidth={2}
                      stroke={m.state === 'at_risk' ? theme.color.warning : theme.color.textMuted}
                      data-testid={`forecast-${m.name}`}
                    />
                  </g>
                )}
              </g>
            );
          })}
          <line
            x1={todayX + px / 2}
            x2={todayX + px / 2}
            y1={0}
            y2={height}
            stroke={theme.color.accent}
            strokeWidth={2}
          >
            <title>{t('timeline.today')}</title>
          </line>
          {data.dependencies.map((d) => {
            const a = index.get(d.blocker);
            const b = index.get(d.blocked);
            if (a === undefined || b === undefined) return null;
            if (Math.max(a, b) < from || Math.min(a, b) > to) return null;
            const blocker = rows[a];
            const blocked = rows[b];
            if (blocker?.kind !== 'ticket' || blocked?.kind !== 'ticket') return null;
            const sa = spanOf(blocker.ticket.start_date, blocker.ticket.due_date);
            const sb = spanOf(blocked.ticket.start_date, blocked.ticket.due_date);
            if (!sa || !sb) return null;
            const color = d.conflict ? theme.color.danger : theme.color.textMuted;
            return (
              <path
                key={`${d.blocker}-${d.blocked}`}
                d={arrowPath(
                  (sa.end - first + 1) * px,
                  a * ROW + ROW / 2,
                  (sb.start - first) * px,
                  b * ROW + ROW / 2,
                )}
                fill="none"
                stroke={color}
                strokeWidth={d.conflict ? 2 : 1.2}
                markerEnd={d.conflict ? 'url(#arrow-danger)' : 'url(#arrow)'}
                data-testid={`dep-${d.blocker}-${d.blocked}`}
                data-conflict={d.conflict}
              >
                <title>{t(d.conflict ? 'timeline.conflict' : 'timeline.blocks', d)}</title>
              </path>
            );
          })}
          <defs>
            <marker
              id="arrow"
              viewBox="0 0 8 8"
              refX="7"
              refY="4"
              markerWidth="7"
              markerHeight="7"
              orient="auto"
            >
              <path d="M0,0 L8,4 L0,8 z" fill={theme.color.textMuted} />
            </marker>
            <marker
              id="arrow-danger"
              viewBox="0 0 8 8"
              refX="7"
              refY="4"
              markerWidth="7"
              markerHeight="7"
              orient="auto"
            >
              <path d="M0,0 L8,4 L0,8 z" fill={theme.color.danger} />
            </marker>
          </defs>
          {visible.map((row, i) =>
            row.kind === 'ticket' ? (
              <TicketBar
                key={row.key}
                ticket={row.ticket}
                y={(from + i) * ROW}
                height={ROW}
                origin={first}
                px={px}
                canEdit={canEdit}
                onOpen={() => onOpen(row.key)}
                onCommit={(next) => onChange(row.ticket, next)}
              />
            ) : null,
          )}
        </svg>
      </S.Chart>
    </S.Wrapper>
  );
}
