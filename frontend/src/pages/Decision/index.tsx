import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Table, Button, Space, Tag, Input, Select,
  Popconfirm, Row, Col, Form, Modal, InputNumber,
  Slider, Descriptions, Timeline, Progress,  App } from 'antd';
import {
  PlusOutlined, SearchOutlined, ReloadOutlined,
  EyeOutlined, EditOutlined, DeleteOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import {
  getDecisionList, createDecision, getDecision, updateDecision, deleteDecision,
} from '@/services/decision';
import { getTenderList } from '@/services/tender';
import { getUserList } from '@/services/system';
import { getApprovalDetail } from '@/services/approval';

// ── 状态映射 ───────────────────────────────────────────────
const DECISION_RESULT_MAP: Record<string, { color: string; label: string }> = {
  PENDING: { color: 'blue',    label: '待决策' },
  PASS:    { color: 'green',   label: '通过'   },
  REJECT:  { color: 'red',     label: '未通过' },
};

const APPROVAL_STATUS_MAP: Record<string, { color: string; label: string }> = {
  PENDING:  { color: 'processing', label: '审批中' },
  APPROVED: { color: 'success',    label: '已通过' },
  REJECTED: { color: 'error',      label: '已驳回' },
};

const WIN_PROB_COLOR = (p: number) => {
  if (p >= 70) return '#0d9488';
  if (p >= 40) return '#f59e0b';
  return '#ef4444';
};

// ── DecisionForm 组件 ─────────────────────────────────────
interface DecisionFormProps {
  open: boolean;
  mode: 'create' | 'edit';
  initialValues?: Partial<BidDecision>;
  onOk: (values: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
}

function DecisionForm({ open, mode, initialValues, onOk, onCancel }: DecisionFormProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [tenderOptions, setTenderOptions] = useState<{ value: number; label: string }[]>([]);
  const [userOptions, setUserOptions] = useState<{ value: number; label: string }[]>([]);
  const [probValue, setProbValue] = useState<number>(50);

  useEffect(() => {
    if (open) {
      form.resetFields();
      if (initialValues) {
        form.setFieldsValue(initialValues);
        setProbValue(initialValues.win_probability ?? 50);
      } else {
        setProbValue(50);
      }
    }
  }, [open, initialValues, form]);

  useEffect(() => {
    if (!open) return;
    Promise.all([
      getTenderList({ status: 'PENDING', page: 1, page_size: 100 }),
      getUserList({ page: 1, page_size: 100 }),
    ]).then(([tRes, uRes]) => {
      setTenderOptions(tRes.data.items.map((t: Tender) => ({ value: t.id, label: t.title })));
      setUserOptions(uRes.data.items.map((u: SystemUser) => ({ value: u.id, label: u.real_name })));
    }).catch(() => {});
  }, [open]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      await onOk(values);
    } finally {
      setLoading(false);
    }
  };

  const sliderMarks = { 0: '0%', 25: '25%', 50: '50%', 75: '75%', 100: '100%' };

  return (
    <Modal
      title={mode === 'create' ? '新增投标决策' : '编辑投标决策'}
      open={open}
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={loading}
      width={680}
      okText={mode === 'create' ? '创建' : '保存'}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" style={{ maxHeight: '65vh', overflowY: 'auto', paddingRight: 8 }}>
        <Form.Item name="tender_id" label="招标项目" rules={[{ required: true, message: '请选择招标项目' }]}>
          <Select
            placeholder="选择招标项目"
            showSearch
            optionFilterProp="label"
            options={tenderOptions}
            disabled={mode === 'edit'}
          />
        </Form.Item>

        <Form.Item name="decision_reason" label="投标理由">
          <Input.TextArea rows={3} placeholder="请输入投标理由" />
        </Form.Item>

        <Form.Item name="risk_analysis" label="风险分析">
          <Input.TextArea rows={3} placeholder="请输入风险分析" />
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="estimated_amount" label="预估报价">
              <InputNumber
                precision={4}
                min={0}
                addonAfter="万元"
                style={{ width: '100%' }}
                placeholder="请输入预估报价"
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="win_probability" label="中标概率">
              <Slider
                min={0}
                max={100}
                marks={sliderMarks}
                tooltip={{ formatter: (v) => `${v}%` }}
                onChange={(v) => setProbValue(v)}
              />
              <div style={{ textAlign: 'center', marginTop: -8, color: WIN_PROB_COLOR(probValue), fontWeight: 600 }}>
                {probValue}%
              </div>
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="competitors" label="竞争对手">
          <Input.TextArea rows={2} placeholder="请输入竞争对手信息" />
        </Form.Item>

        {mode === 'create' && (
          <Form.Item name="approver_id" label="审批人" rules={[{ required: true, message: '请选择审批人' }]}>
            <Select
              placeholder="选择审批人"
              showSearch
              optionFilterProp="label"
              options={userOptions}
            />
          </Form.Item>
        )}

        <Form.Item name="remark" label="备注">
          <Input.TextArea rows={2} placeholder="备注信息" />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ── DetailModal 组件 ──────────────────────────────────────
interface DetailModalProps {
  open: boolean;
  record: BidDecision | null;
  onClose: () => void;
}

function DetailModal({ open, record, onClose }: DetailModalProps) {
  const navigate = useNavigate();
  const [approvalDetail, setApprovalDetail] = useState<ApprovalDetail | null>(null);

  useEffect(() => {
    if (open && record?.approval_id) {
      getApprovalDetail(record.approval_id)
        .then((res) => setApprovalDetail(res.data))
        .catch(() => setApprovalDetail(null));
    } else {
      setApprovalDetail(null);
    }
  }, [open, record]);

  if (!record) return null;

  const dr = DECISION_RESULT_MAP[record.decision_result] || { color: 'default', label: record.decision_result };
  const as = record.approval_status ? (APPROVAL_STATUS_MAP[record.approval_status] || { color: 'default', label: record.approval_status }) : null;

  const timelineItems = approvalDetail?.records.map((r) => {
    const actionLabel: Record<string, string> = {
      SUBMIT: '提交',
      APPROVE: '审批通过',
      REJECT: '审批驳回',
      TRANSFER: '转审',
    };
    return {
      key: r.id,
      color: r.action === 'APPROVE' ? 'green' : r.action === 'REJECT' ? 'red' : 'blue',
      children: (
        <div>
          <div><strong>{r.operator_name}</strong> — {actionLabel[r.action] || r.action}</div>
          {r.comment && <div style={{ color: '#64748b', marginTop: 2 }}>{r.comment}</div>}
          <div style={{ color: '#94a3b8', fontSize: 12, marginTop: 2 }}>
            {r.created_at ? dayjs(r.created_at).format('YYYY-MM-DD HH:mm') : ''}
          </div>
        </div>
      ),
    };
  });

  return (
    <Modal
      title="投标决策详情"
      open={open}
      onCancel={onClose}
      footer={<Button onClick={onClose}>关闭</Button>}
      width={700}
      destroyOnHidden
    >
      <Descriptions column={2} bordered size="small" style={{ marginBottom: 16 }}>
        <Descriptions.Item label="招标项目" span={2}>
          <a onClick={() => navigate(`/tender/${record.tender_id}`)}>{record.tender_title || '-'}</a>
        </Descriptions.Item>
        <Descriptions.Item label="招标编号">{record.tender_no || '-'}</Descriptions.Item>
        <Descriptions.Item label="发起人">{record.initiator_name || '-'}</Descriptions.Item>
        <Descriptions.Item label="决策结果">
          <Tag color={dr.color}>{dr.label}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="审批状态">
          {as ? <Tag color={as.color}>{as.label}</Tag> : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="预估报价">
          {record.estimated_amount !== undefined && record.estimated_amount !== null
            ? `${record.estimated_amount} 万元` : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="中标概率">
          {record.win_probability !== undefined && record.win_probability !== null ? (
            <Progress
              percent={record.win_probability}
              size="small"
              strokeColor={WIN_PROB_COLOR(record.win_probability)}
              style={{ width: 140 }}
            />
          ) : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="投标理由" span={2}>{record.decision_reason || '-'}</Descriptions.Item>
        <Descriptions.Item label="风险分析" span={2}>{record.risk_analysis || '-'}</Descriptions.Item>
        <Descriptions.Item label="竞争对手" span={2}>{record.competitors || '-'}</Descriptions.Item>
        <Descriptions.Item label="备注" span={2}>{record.remark || '-'}</Descriptions.Item>
        <Descriptions.Item label="创建时间" span={2}>
          {record.created_at ? dayjs(record.created_at).format('YYYY-MM-DD HH:mm') : '-'}
        </Descriptions.Item>
      </Descriptions>

      {approvalDetail && timelineItems && timelineItems.length > 0 && (
        <Card title="审批记录" size="small" style={{ background: '#f8fafc' }}>
          <Timeline items={timelineItems} style={{ marginTop: 8 }} />
        </Card>
      )}
    </Modal>
  );
}

// ── 主页面 ────────────────────────────────────────────────
export default function DecisionPage() {
  const { message } = App.useApp();
  const [form] = Form.useForm();

  const [data, setData] = useState<BidDecision[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  // Modal states
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<BidDecision | null>(null);

  const loadData = useCallback(async (currentPage = page) => {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      const params: Record<string, unknown> = { page: currentPage, page_size: 20 };
      if (values.keyword) params.keyword = values.keyword;
      if (values.decision_result) params.decision_result = values.decision_result;

      const res = await getDecisionList(params);
      setData(res.data.items);
      setTotal(res.data.total);
    } finally {
      setLoading(false);
    }
  }, [form, page]);

  useEffect(() => {
    loadData(page);
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = () => { setPage(1); loadData(1); };
  const handleReset = () => { form.resetFields(); setPage(1); loadData(1); };

  const handleCreate = async (values: Record<string, unknown>) => {
    await createDecision(values);
    message.success('创建成功');
    setCreateOpen(false);
    loadData(1);
  };

  const handleEdit = async (values: Record<string, unknown>) => {
    if (!currentRecord) return;
    await updateDecision(currentRecord.id, values);
    message.success('更新成功');
    setEditOpen(false);
    loadData(page);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteDecision(id);
      message.success('删除成功');
      loadData(page);
    } catch {
      message.error('删除失败');
    }
  };

  const openDetail = async (r: BidDecision) => {
    // Refresh detail from server
    try {
      const res = await getDecision(r.id);
      setCurrentRecord(res.data);
    } catch {
      setCurrentRecord(r);
    }
    setDetailOpen(true);
  };

  const openEdit = (r: BidDecision) => {
    setCurrentRecord(r);
    setEditOpen(true);
  };

  const columns: ColumnsType<BidDecision> = [
    {
      title: '招标项目',
      dataIndex: 'tender_title',
      key: 'tender_title',
      ellipsis: true,
      render: (v: string | undefined, r: BidDecision) => (
        <a href={`/tender/${r.tender_id}`} onClick={(e) => { e.preventDefault(); window.location.href = `/tender/${r.tender_id}`; }}>
          {v || '-'}
        </a>
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
      title: '预估报价(万元)',
      dataIndex: 'estimated_amount',
      key: 'estimated_amount',
      width: 130,
      render: (v?: number) => (v !== undefined && v !== null) ? `${v} 万元` : '-',
    },
    {
      title: '中标概率',
      dataIndex: 'win_probability',
      key: 'win_probability',
      width: 150,
      render: (v?: number) => {
        if (v === undefined || v === null) return '-';
        return (
          <Progress
            percent={v}
            size="small"
            strokeColor={WIN_PROB_COLOR(v)}
            style={{ width: 120 }}
          />
        );
      },
    },
    {
      title: '决策结果',
      dataIndex: 'decision_result',
      key: 'decision_result',
      width: 100,
      render: (v: string) => {
        const s = DECISION_RESULT_MAP[v] || { color: 'default', label: v };
        return <Tag color={s.color}>{s.label}</Tag>;
      },
    },
    {
      title: '审批状态',
      dataIndex: 'approval_status',
      key: 'approval_status',
      width: 100,
      render: (v?: string) => {
        if (!v) return '-';
        const s = APPROVAL_STATUS_MAP[v] || { color: 'default', label: v };
        return <Tag color={s.color}>{s.label}</Tag>;
      },
    },
    {
      title: '发起人',
      dataIndex: 'initiator_name',
      key: 'initiator_name',
      width: 90,
      render: (v?: string) => v || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (v?: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_: unknown, r: BidDecision) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => openDetail(r)}
          >
            详情
          </Button>
          {r.decision_result === 'PENDING' && (
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => openEdit(r)}
            >
              编辑
            </Button>
          )}
          <Popconfirm
            title="确定删除该决策记录？"
            onConfirm={() => handleDelete(r.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* 筛选栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline">
          <Row gutter={[12, 12]} style={{ width: '100%' }}>
            <Col span={8}>
              <Form.Item name="keyword" style={{ margin: 0 }}>
                <Input placeholder="搜索招标名称" prefix={<SearchOutlined />} allowClear />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="decision_result" style={{ margin: 0 }}>
                <Select
                  placeholder="决策结果"
                  allowClear
                  style={{ width: '100%' }}
                  options={Object.entries(DECISION_RESULT_MAP).map(([v, s]) => ({ value: v, label: s.label }))}
                />
              </Form.Item>
            </Col>
            <Col span={10} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
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

      {/* 列表 */}
      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ color: '#475569' }}>共 {total} 条记录</span>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateOpen(true)}
            style={{ background: 'linear-gradient(135deg, #0d9488, #14b8a6)', border: 'none' }}
          >
            新增决策
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

      {/* 新增 Modal */}
      <DecisionForm
        open={createOpen}
        mode="create"
        onOk={handleCreate}
        onCancel={() => setCreateOpen(false)}
      />

      {/* 编辑 Modal */}
      <DecisionForm
        open={editOpen}
        mode="edit"
        initialValues={currentRecord ?? undefined}
        onOk={handleEdit}
        onCancel={() => setEditOpen(false)}
      />

      {/* 详情 Modal */}
      <DetailModal
        open={detailOpen}
        record={currentRecord}
        onClose={() => setDetailOpen(false)}
      />
    </div>
  );
}
