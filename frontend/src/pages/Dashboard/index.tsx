import { useEffect, useState } from 'react';
import { Card, Col, Row, Statistic, Table, Tag, Typography, Spin, List } from 'antd';
import {
  FileTextOutlined,
  TrophyOutlined,
  RiseOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { useNavigate } from 'react-router-dom';
import { getDashboardStats } from '@/services/dashboard';

const { Text } = Typography;

const STATUS_COLORS: Record<string, string> = {
  PENDING: '#3b82f6',
  DECIDED_BID: '#22c55e',
  DECIDED_GIVE_UP: '#94a3b8',
  COMPOSING: '#f59e0b',
  SUBMITTED: '#8b5cf6',
  OPENED: '#0d9488',
};

const DEADLINE_TYPE_LABELS: Record<string, string> = {
  reg_deadline: '报名截止',
  deposit_deadline: '保证金截止',
  open_bid_time: '开标',
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    getDashboardStats()
      .then((res) => {
        if (res.code === 200 && res.data) {
          setStats(res.data);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  const cards = stats?.cards;
  const statusDist = stats?.status_distribution ?? [];
  const monthlyTrend = stats?.monthly_trend ?? [];
  const expiringList = stats?.expiring_list ?? [];
  const pendingApprovals = stats?.pending_approvals ?? [];

  // --- Pie chart option ---
  const pieOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle', textStyle: { color: '#475569' } },
    series: [
      {
        name: '招标状态',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        data: statusDist.map((item) => ({
          value: item.count,
          name: item.label,
          itemStyle: { color: STATUS_COLORS[item.status] ?? '#cbd5e1' },
        })),
        graphic: [
          {
            type: 'text',
            left: '55%',
            top: '45%',
            style: {
              text: `${statusDist.reduce((acc, i) => acc + i.count, 0)}`,
              textAlign: 'center',
              fill: '#0f172a',
              fontSize: 22,
              fontWeight: 'bold',
            },
          },
          {
            type: 'text',
            left: '55%',
            top: '55%',
            style: {
              text: '总项目',
              textAlign: 'center',
              fill: '#94a3b8',
              fontSize: 12,
            },
          },
        ],
      },
    ],
  };

  // --- Line chart option ---
  const months = monthlyTrend.map((m) => m.month);
  const lineOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['投标数', '中标数'], top: 8 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: months, boundaryGap: false },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        name: '投标数',
        type: 'line',
        smooth: true,
        data: monthlyTrend.map((m) => m.bid_count),
        itemStyle: { color: '#3b82f6' },
        areaStyle: { color: 'rgba(59,130,246,0.12)' },
      },
      {
        name: '中标数',
        type: 'line',
        smooth: true,
        data: monthlyTrend.map((m) => m.win_count),
        itemStyle: { color: '#22c55e' },
        areaStyle: { color: 'rgba(34,197,94,0.12)' },
      },
    ],
  };

  const expiringColumns = [
    {
      title: '项目名称',
      dataIndex: 'title',
      ellipsis: true,
      render: (text: string, record: DashboardStats['expiring_list'][0]) => (
        <a onClick={() => navigate(`/tender/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'deadline_type',
      width: 90,
      render: (type: string) => (
        <Tag color="blue">{DEADLINE_TYPE_LABELS[type] ?? type}</Tag>
      ),
    },
    {
      title: '截止日期',
      dataIndex: 'deadline',
      width: 100,
    },
    {
      title: '剩余',
      dataIndex: 'days_left',
      width: 72,
      render: (days: number) => (
        <Text style={{ color: days <= 3 ? '#ef4444' : days <= 7 ? '#f97316' : '#22c55e', fontWeight: 600 }}>
          {days}天
        </Text>
      ),
    },
  ];

  const approvalColumns = [
    {
      title: '审批标题',
      dataIndex: 'title',
      ellipsis: true,
      render: (text: string) => (
        <a onClick={() => navigate('/workflow')}>{text}</a>
      ),
    },
    {
      title: '发起人',
      dataIndex: 'initiator_name',
      width: 80,
    },
    {
      title: '发起时间',
      dataIndex: 'created_at',
      width: 110,
      render: (val: string) => val?.slice(0, 10),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Row 1: Stats cards */}
      <Row gutter={16}>
        <Col span={6}>
          <Card
            style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.08)', transition: 'box-shadow 0.2s' }}
            hoverable
          >
            <Statistic
              title="在投项目数"
              value={cards?.active_tenders ?? 0}
              prefix={<FileTextOutlined style={{ color: '#3b82f6' }} />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card
            style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.08)', transition: 'box-shadow 0.2s' }}
            hoverable
          >
            <Statistic
              title="本年中标数"
              value={cards?.win_count_year ?? 0}
              prefix={<TrophyOutlined style={{ color: '#22c55e' }} />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card
            style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.08)', transition: 'box-shadow 0.2s' }}
            hoverable
          >
            <Statistic
              title="中标率"
              value={cards?.win_rate ?? 0}
              suffix="%"
              precision={1}
              prefix={<RiseOutlined style={{ color: '#0d9488' }} />}
              valueStyle={{ color: '#0d9488' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card
            style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.08)', transition: 'box-shadow 0.2s' }}
            hoverable
          >
            <Statistic
              title="即将截止（7天内）"
              value={cards?.expiring_7days ?? 0}
              prefix={<WarningOutlined style={{ color: (cards?.expiring_7days ?? 0) > 0 ? '#ef4444' : '#22c55e' }} />}
              valueStyle={{ color: (cards?.expiring_7days ?? 0) > 0 ? '#ef4444' : '#22c55e' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Row 2: Charts */}
      <Row gutter={16}>
        <Col span={12}>
          <Card
            title="招标状态分布"
            style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }}
          >
            <ReactECharts option={pieOption} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card
            title="月度投标趋势"
            style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }}
          >
            <ReactECharts option={lineOption} style={{ height: 280 }} />
          </Card>
        </Col>
      </Row>

      {/* Row 3: Lists */}
      <Row gutter={16}>
        <Col span={12}>
          <Card
            title="近期截止提醒"
            style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }}
          >
            {expiringList.length === 0 ? (
              <List locale={{ emptyText: '近7天无截止提醒' }} dataSource={[]} renderItem={() => null} />
            ) : (
              <Table
                dataSource={expiringList}
                columns={expiringColumns}
                rowKey="id"
                pagination={false}
                size="small"
              />
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card
            title="待办审批"
            style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }}
          >
            {pendingApprovals.length === 0 ? (
              <List locale={{ emptyText: '暂无待办审批' }} dataSource={[]} renderItem={() => null} />
            ) : (
              <Table
                dataSource={pendingApprovals}
                columns={approvalColumns}
                rowKey="id"
                pagination={false}
                size="small"
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
