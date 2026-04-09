import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, Card, Tag, Badge, Spin } from 'antd';
import type { Dayjs } from 'dayjs';
import { getTenderCalendar } from '@/services/tender';

const TYPE_CONFIG: Record<string, { color: string; label: string }> = {
  reg_deadline:    { color: 'blue',   label: '报名截止' },
  deposit_deadline:{ color: 'orange', label: '保证金截止' },
  open_bid:        { color: 'red',    label: '开标' },
};

export default function TenderCalendarPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [calendarData, setCalendarData] = useState<TenderCalendarItem[]>([]);
  const [currentMonth, setCurrentMonth] = useState<{ year: number; month: number }>(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() + 1 };
  });

  const loadCalendar = useCallback(async (year: number, month: number) => {
    setLoading(true);
    try {
      const res = await getTenderCalendar(year, month);
      setCalendarData(res.data);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCalendar(currentMonth.year, currentMonth.month);
  }, [currentMonth, loadCalendar]);

  const handlePanelChange = (value: Dayjs) => {
    setCurrentMonth({ year: value.year(), month: value.month() + 1 });
  };

  const cellRender = (current: Dayjs) => {
    const dateStr = current.format('YYYY-MM-DD');
    const dayItems = calendarData.filter((item) => item.date === dateStr);
    if (dayItems.length === 0) return null;

    return (
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {dayItems.map((item, idx) => {
          const cfg = TYPE_CONFIG[item.type] || { color: 'default', label: item.label };
          return (
            <li key={`${item.id}-${item.type}-${idx}`} style={{ marginBottom: 2 }}>
              <Tag
                color={cfg.color}
                style={{
                  fontSize: 11,
                  padding: '0 4px',
                  cursor: 'pointer',
                  maxWidth: '100%',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  display: 'block',
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/tender/${item.id}`);
                }}
                title={`${cfg.label}: ${item.title}`}
              >
                {cfg.label}: {item.title}
              </Tag>
            </li>
          );
        })}
      </ul>
    );
  };

  return (
    <Card
      title="招标日历视图"
      extra={
        <div style={{ fontSize: 13, color: '#64748b' }}>
          <Badge color="blue" text="报名截止" style={{ marginRight: 12 }} />
          <Badge color="orange" text="保证金截止" style={{ marginRight: 12 }} />
          <Badge color="red" text="开标" />
        </div>
      }
    >
      <Spin spinning={loading}>
        <Calendar
          cellRender={cellRender}
          onPanelChange={handlePanelChange}
        />
      </Spin>
    </Card>
  );
}
