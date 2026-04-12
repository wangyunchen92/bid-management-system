import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Table, Button, Space, Tag, Input, Select, DatePicker,
  Popconfirm, Row, Col, Form,  App } from 'antd';
import { PlusOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { getTenderList, deleteTender } from '@/services/tender';
import { getUserList } from '@/services/system';
import useDictStore from '@/stores/useDictStore';

const { RangePicker } = DatePicker;

const STATUS_TAG_MAP: Record<string, { color: string; label: string }> = {
  PENDING:         { color: 'blue',    label: '待决策' },
  DECIDED_BID:     { color: 'green',   label: '决定投标' },
  DECIDED_GIVE_UP: { color: 'default', label: '决定放弃' },
  COMPOSING:       { color: 'orange',  label: '标书编制' },
  SUBMITTED:       { color: 'purple',  label: '已提交' },
  OPENED:          { color: 'cyan',    label: '已开标' },
};

export default function TenderListPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { getDictItems } = useDictStore();
  const [form] = Form.useForm();

  const [data, setData] = useState<Tender[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  const [tenderMethodOptions, setTenderMethodOptions] = useState<{ value: string; label: string }[]>([]);
  const [infoSourceOptions, setInfoSourceOptions] = useState<{ value: string; label: string }[]>([]);
  const [statusOptions, setStatusOptions] = useState<{ value: string; label: string }[]>([]);
  const [userOptions, setUserOptions] = useState<{ value: number; label: string }[]>([]);

  const loadDicts = useCallback(async () => {
    const [methods, sources, statuses] = await Promise.all([
      getDictItems('tender_method'),
      getDictItems('tender_info_source'),
      getDictItems('tender_status'),
    ]);
    setTenderMethodOptions(methods.map((d) => ({ value: d.item_value, label: d.item_label })));
    setInfoSourceOptions(sources.map((d) => ({ value: d.item_value, label: d.item_label })));
    setStatusOptions(statuses.map((d) => ({ value: d.item_value, label: d.item_label })));
  }, [getDictItems]);

  const loadUsers = useCallback(async () => {
    const res = await getUserList({ page: 1, page_size: 100 });
    setUserOptions(res.data.items.map((u: SystemUser) => ({ value: u.id, label: u.real_name })));
  }, []);

  const loadData = useCallback(async (currentPage = page) => {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      const params: Record<string, unknown> = {
        page: currentPage,
        page_size: 20,
      };
      if (values.keyword) params.keyword = values.keyword;
      if (values.tender_method) params.tender_method = values.tender_method;
      if (values.info_source) params.info_source = values.info_source;
      if (values.status) params.status = values.status;
      if (values.follower_id) params.follower_id = values.follower_id;
      if (values.date_range && values.date_range[0]) {
        params.start_date = values.date_range[0].format('YYYY-MM-DD');
      }
      if (values.date_range && values.date_range[1]) {
        params.end_date = values.date_range[1].format('YYYY-MM-DD');
      }

      const res = await getTenderList(params);
      setData(res.data.items);
      setTotal(res.data.total);
    } finally {
      setLoading(false);
    }
  }, [form, page]);

  useEffect(() => {
    loadDicts();
    loadUsers();
  }, [loadDicts, loadUsers]);

  useEffect(() => {
    loadData(page);
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = () => {
    setPage(1);
    loadData(1);
  };

  const handleReset = () => {
    form.resetFields();
    setPage(1);
    loadData(1);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteTender(id);
      message.success('删除成功');
      loadData(page);
    } catch {
      message.error('删除失败');
    }
  };

  const columns: ColumnsType<Tender> = [
    {
      title: '项目名称',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (v: string, r: Tender) => (
        <a onClick={() => navigate(`/tender/${r.id}`)}>{v}</a>
      ),
    },
    {
      title: '招标编号',
      dataIndex: 'tender_no',
      key: 'tender_no',
      width: 140,
      render: (v?: string) => v || '-',
    },
    {
      title: '招标单位',
      dataIndex: 'tender_unit',
      key: 'tender_unit',
      ellipsis: true,
      render: (v?: string) => v || '-',
    },
    {
      title: '招标方式',
      dataIndex: 'tender_method',
      key: 'tender_method',
      width: 100,
      render: (v?: string) => {
        const opt = tenderMethodOptions.find((o) => o.value === v);
        return opt ? opt.label : (v || '-');
      },
    },
    {
      title: '预算金额(万元)',
      dataIndex: 'budget_amount',
      key: 'budget_amount',
      width: 130,
      render: (v?: number) => (v !== undefined && v !== null) ? `${v} 万元` : '-',
    },
    {
      title: '开标时间',
      dataIndex: 'open_bid_time',
      key: 'open_bid_time',
      width: 160,
      render: (v?: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (v: string) => {
        const s = STATUS_TAG_MAP[v] || { color: 'default', label: v };
        return <Tag color={s.color}>{s.label}</Tag>;
      },
    },
    {
      title: '跟进人',
      dataIndex: 'follower_name',
      key: 'follower_name',
      width: 90,
      render: (v?: string) => v || '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 140,
      render: (_: unknown, r: Tender) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/tender/${r.id}?edit=1`)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除该招标信息？"
            onConfirm={() => handleDelete(r.id)}
          >
            <Button type="link" size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline">
          <Row gutter={[12, 12]} style={{ width: '100%' }}>
            <Col span={6}>
              <Form.Item name="keyword" style={{ margin: 0 }}>
                <Input placeholder="搜索项目名称/招标编号" prefix={<SearchOutlined />} allowClear />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="tender_method" style={{ margin: 0 }}>
                <Select
                  placeholder="招标方式"
                  allowClear
                  options={tenderMethodOptions}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="info_source" style={{ margin: 0 }}>
                <Select
                  placeholder="信息来源"
                  allowClear
                  options={infoSourceOptions}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="status" style={{ margin: 0 }}>
                <Select
                  placeholder="状态"
                  allowClear
                  options={statusOptions.length > 0 ? statusOptions : Object.entries(STATUS_TAG_MAP).map(([v, s]) => ({ value: v, label: s.label }))}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="follower_id" style={{ margin: 0 }}>
                <Select
                  placeholder="跟进人"
                  allowClear
                  options={userOptions}
                  showSearch
                  optionFilterProp="label"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="date_range" style={{ margin: 0 }}>
                <RangePicker
                  placeholder={['开标开始', '开标结束']}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col span={16} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
                查询
              </Button>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                重置
              </Button>
            </Col>
          </Row>
        </Form>
      </Card>

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ color: '#475569' }}>共 {total} 条记录</span>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/tender/create')}
            style={{ background: 'linear-gradient(135deg, #0d9488, #14b8a6)', border: 'none' }}
          >
            新增招标
          </Button>
        </div>

        <Table
          dataSource={data}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="middle"
          pagination={{
            current: page,
            total,
            pageSize: 20,
            showSizeChanger: false,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p) => setPage(p),
          }}
        />
      </Card>
    </div>
  );
}
