import { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Space, Tag, Input, Select,
  Popconfirm, message, Row, Col, Form, Modal, InputNumber,
  Descriptions, Typography, DatePicker,
} from 'antd';
import {
  PlusOutlined, SearchOutlined, ReloadOutlined,
  EyeOutlined, EditOutlined, DeleteOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import {
  getOpeningList, createOpening, getOpening, updateOpening, deleteOpening,
} from '@/services/opening';
import { getTenderList } from '@/services/tender';

const { Paragraph } = Typography;

// ── 结果映射 ─────────────────────────────────────────────────
const RESULT_MAP: Record<string, { color: string; label: string }> = {
  WIN:     { color: 'green',   label: '中标'   },
  LOSE:    { color: 'default', label: '未中标' },
  INVALID: { color: 'red',     label: '废标'   },
  ABORTED: { color: 'orange',  label: '流标'   },
};

const RESULT_OPTIONS = Object.entries(RESULT_MAP).map(([v, s]) => ({ value: v, label: s.label }));

// ── OpeningForm 组件 ──────────────────────────────────────────
interface OpeningFormProps {
  open: boolean;
  mode: 'create' | 'edit';
  initialValues?: Partial<BidOpening>;
  onOk: (values: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
}

function OpeningForm({ open, mode, initialValues, onOk, onCancel }: OpeningFormProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [tenderOptions, setTenderOptions] = useState<{ value: number; label: string }[]>([]);

  useEffect(() => {
    if (open) {
      form.resetFields();
      if (initialValues) {
        form.setFieldsValue({
          ...initialValues,
          opening_time: initialValues.opening_time ? dayjs(initialValues.opening_time) : undefined,
        });
      }
    }
  }, [open, initialValues, form]);

  useEffect(() => {
    if (!open) return;
    getTenderList({ page: 1, page_size: 200 })
      .then((res) => {
        setTenderOptions(res.data.items.map((t: Tender) => ({ value: t.id, label: t.title })));
      })
      .catch(() => {});
  }, [open]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      if (values.opening_time) {
        values.opening_time = values.opening_time.toISOString();
      }
      setLoading(true);
      await onOk(values);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={mode === 'create' ? '新增开标记录' : '编辑开标记录'}
      open={open}
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={loading}
      width={680}
      okText={mode === 'create' ? '创建' : '保存'}
      destroyOnClose
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

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="opening_time" label="开标时间">
              <DatePicker showTime style={{ width: '100%' }} placeholder="选择开标时间" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="result" label="开标结果">
              <Select placeholder="请选择开标结果" allowClear options={RESULT_OPTIONS} />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="our_price" label="我方报价">
              <InputNumber
                precision={4}
                min={0}
                addonAfter="万元"
                style={{ width: '100%' }}
                placeholder="请输入我方报价"
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="win_price" label="中标价">
              <InputNumber
                precision={4}
                min={0}
                addonAfter="万元"
                style={{ width: '100%' }}
                placeholder="请输入中标价"
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="win_company" label="中标单位">
          <Input placeholder="请输入中标单位" />
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="total_bidders" label="投标家数">
              <InputNumber min={1} style={{ width: '100%' }} placeholder="请输入投标家数" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="ranking" label="我方排名">
              <InputNumber min={1} style={{ width: '100%' }} placeholder="请输入我方排名" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="remark" label="备注">
          <Input.TextArea rows={2} placeholder="备注信息" />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ── ReviewForm 组件（复盘编辑） ───────────────────────────────
interface ReviewFormProps {
  open: boolean;
  initialValues?: Partial<BidOpening>;
  onOk: (values: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
}

function ReviewForm({ open, initialValues, onOk, onCancel }: ReviewFormProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      form.resetFields();
      if (initialValues) {
        form.setFieldsValue({
          review_summary: initialValues.review_summary,
          lessons_learned: initialValues.lessons_learned,
        });
      }
    }
  }, [open, initialValues, form]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      await onOk(values);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="编辑复盘"
      open={open}
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={loading}
      width={600}
      okText="保存"
      destroyOnClose
    >
      <Form form={form} layout="vertical">
        <Form.Item name="review_summary" label="复盘总结">
          <Input.TextArea rows={4} placeholder="请输入复盘总结" />
        </Form.Item>
        <Form.Item name="lessons_learned" label="经验教训">
          <Input.TextArea rows={4} placeholder="请输入经验教训" />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ── DetailModal 组件 ──────────────────────────────────────────
interface DetailModalProps {
  open: boolean;
  record: BidOpening | null;
  onClose: () => void;
  onEditReview: () => void;
}

function DetailModal({ open, record, onClose, onEditReview }: DetailModalProps) {
  if (!record) return null;

  const resultInfo = record.result ? (RESULT_MAP[record.result] || { color: 'default', label: record.result }) : null;

  return (
    <Modal
      title="开标详情"
      open={open}
      onCancel={onClose}
      footer={
        <Space>
          <Button onClick={onEditReview} type="default">
            编辑复盘
          </Button>
          <Button onClick={onClose} type="primary">
            关闭
          </Button>
        </Space>
      }
      width={700}
      destroyOnClose
    >
      <Descriptions column={2} bordered size="small" style={{ marginBottom: 16 }}>
        <Descriptions.Item label="招标项目" span={2}>
          {record.tender_title || '-'}
        </Descriptions.Item>
        <Descriptions.Item label="招标编号">{record.tender_no || '-'}</Descriptions.Item>
        <Descriptions.Item label="开标时间">
          {record.opening_time ? dayjs(record.opening_time).format('YYYY-MM-DD HH:mm') : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="开标结果">
          {resultInfo ? <Tag color={resultInfo.color}>{resultInfo.label}</Tag> : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="中标单位">{record.win_company || '-'}</Descriptions.Item>
        <Descriptions.Item label="我方报价">
          {record.our_price !== undefined && record.our_price !== null ? `${record.our_price} 万元` : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="中标价">
          {record.win_price !== undefined && record.win_price !== null ? `${record.win_price} 万元` : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="投标家数">
          {record.total_bidders !== undefined && record.total_bidders !== null ? `${record.total_bidders} 家` : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="我方排名">
          {record.ranking !== undefined && record.ranking !== null ? `第 ${record.ranking} 名` : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="备注" span={2}>{record.remark || '-'}</Descriptions.Item>
        <Descriptions.Item label="创建时间" span={2}>
          {record.created_at ? dayjs(record.created_at).format('YYYY-MM-DD HH:mm') : '-'}
        </Descriptions.Item>
      </Descriptions>

      {(record.review_summary || record.lessons_learned) && (
        <Card title="复盘记录" size="small" style={{ background: '#f0fdfa' }}>
          {record.review_summary && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontWeight: 600, marginBottom: 4, color: '#0f172a' }}>复盘总结</div>
              <Paragraph style={{ margin: 0, color: '#475569' }}>{record.review_summary}</Paragraph>
            </div>
          )}
          {record.lessons_learned && (
            <div>
              <div style={{ fontWeight: 600, marginBottom: 4, color: '#0f172a' }}>经验教训</div>
              <Paragraph style={{ margin: 0, color: '#475569' }}>{record.lessons_learned}</Paragraph>
            </div>
          )}
        </Card>
      )}
    </Modal>
  );
}

// ── 主页面 ────────────────────────────────────────────────────
export default function OpeningPage() {
  const [form] = Form.useForm();

  const [data, setData] = useState<BidOpening[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<BidOpening | null>(null);

  const loadData = useCallback(async (currentPage = page) => {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      const params: Record<string, unknown> = { page: currentPage, page_size: 20 };
      if (values.keyword) params.keyword = values.keyword;
      if (values.result) params.result = values.result;

      const res = await getOpeningList(params);
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
    await createOpening(values);
    message.success('创建成功');
    setCreateOpen(false);
    loadData(1);
  };

  const handleEdit = async (values: Record<string, unknown>) => {
    if (!currentRecord) return;
    await updateOpening(currentRecord.id, values);
    message.success('更新成功');
    setEditOpen(false);
    loadData(page);
  };

  const handleReviewSave = async (values: Record<string, unknown>) => {
    if (!currentRecord) return;
    await updateOpening(currentRecord.id, values);
    message.success('复盘已保存');
    setReviewOpen(false);
    // Refresh detail record
    try {
      const res = await getOpening(currentRecord.id);
      setCurrentRecord(res.data);
    } catch {
      loadData(page);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteOpening(id);
      message.success('删除成功');
      loadData(page);
    } catch {
      message.error('删除失败');
    }
  };

  const openDetail = async (r: BidOpening) => {
    try {
      const res = await getOpening(r.id);
      setCurrentRecord(res.data);
    } catch {
      setCurrentRecord(r);
    }
    setDetailOpen(true);
  };

  const openEdit = (r: BidOpening) => {
    setCurrentRecord(r);
    setEditOpen(true);
  };

  const openReview = () => {
    setDetailOpen(false);
    setReviewOpen(true);
  };

  const columns: ColumnsType<BidOpening> = [
    {
      title: '招标项目',
      dataIndex: 'tender_title',
      key: 'tender_title',
      ellipsis: true,
      render: (v?: string) => v || '-',
    },
    {
      title: '招标编号',
      dataIndex: 'tender_no',
      key: 'tender_no',
      width: 140,
      render: (v?: string) => v || '-',
    },
    {
      title: '开标时间',
      dataIndex: 'opening_time',
      key: 'opening_time',
      width: 160,
      render: (v?: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '开标结果',
      dataIndex: 'result',
      key: 'result',
      width: 90,
      render: (v?: string) => {
        if (!v) return '-';
        const s = RESULT_MAP[v] || { color: 'default', label: v };
        return <Tag color={s.color}>{s.label}</Tag>;
      },
    },
    {
      title: '我方报价(万元)',
      dataIndex: 'our_price',
      key: 'our_price',
      width: 130,
      render: (v?: number) => (v !== undefined && v !== null) ? v.toString() : '-',
    },
    {
      title: '中标价(万元)',
      dataIndex: 'win_price',
      key: 'win_price',
      width: 120,
      render: (v?: number) => (v !== undefined && v !== null) ? v.toString() : '-',
    },
    {
      title: '中标单位',
      dataIndex: 'win_company',
      key: 'win_company',
      ellipsis: true,
      render: (v?: string) => v || '-',
    },
    {
      title: '投标家数',
      dataIndex: 'total_bidders',
      key: 'total_bidders',
      width: 90,
      render: (v?: number) => (v !== undefined && v !== null) ? `${v} 家` : '-',
    },
    {
      title: '我方排名',
      dataIndex: 'ranking',
      key: 'ranking',
      width: 90,
      render: (v?: number) => (v !== undefined && v !== null) ? `第 ${v} 名` : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_: unknown, r: BidOpening) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => openDetail(r)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEdit(r)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除该开标记录？"
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
                <Input placeholder="搜索招标名称/编号" prefix={<SearchOutlined />} allowClear />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="result" style={{ margin: 0 }}>
                <Select
                  placeholder="开标结果"
                  allowClear
                  style={{ width: '100%' }}
                  options={RESULT_OPTIONS}
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
            新增开标记录
          </Button>
        </div>

        <Table
          dataSource={data}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="middle"
          scroll={{ x: 1200 }}
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
      <OpeningForm
        open={createOpen}
        mode="create"
        onOk={handleCreate}
        onCancel={() => setCreateOpen(false)}
      />

      {/* 编辑 Modal */}
      <OpeningForm
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
        onEditReview={openReview}
      />

      {/* 复盘编辑 Modal */}
      <ReviewForm
        open={reviewOpen}
        initialValues={currentRecord ?? undefined}
        onOk={handleReviewSave}
        onCancel={() => setReviewOpen(false)}
      />
    </div>
  );
}
