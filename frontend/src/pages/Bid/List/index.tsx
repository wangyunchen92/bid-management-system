import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Button, Space, Tag, Input, Select, Row, Col,
  Form, Modal, DatePicker, Popconfirm, message, Empty, Spin,
  Avatar, Typography,
} from 'antd';
import {
  PlusOutlined, SearchOutlined, ReloadOutlined,
  EditOutlined, DeleteOutlined, ArrowRightOutlined,
  UserOutlined, CalendarOutlined, FileTextOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  getBidProjectList, createBidProject, updateBidProject, deleteBidProject,
} from '@/services/bid';
import { getTenderList } from '@/services/tender';
import { getUserList } from '@/services/system';

const { Text } = Typography;

// ── 状态映射 ──────────────────────────────────────────────────
const STATUS_MAP: Record<string, { color: string; label: string }> = {
  DRAFT:       { color: 'default',    label: '草稿'   },
  IN_PROGRESS: { color: 'processing', label: '编制中' },
  REVIEW:      { color: 'warning',    label: '审核中' },
  SUBMITTED:   { color: 'success',    label: '已提交' },
};

const STATUS_OPTIONS = Object.entries(STATUS_MAP).map(([v, s]) => ({ value: v, label: s.label }));

const DOC_TYPE_OPTIONS = [
  { value: 'TECHNICAL', label: '技术标' },
  { value: 'COMMERCIAL', label: '商务标' },
  { value: 'PRICE', label: '报价标' },
  { value: 'COMPREHENSIVE', label: '综合标' },
];

// ── ProjectFormModal 组件 ────────────────────────────────────
interface ProjectFormProps {
  open: boolean;
  mode: 'create' | 'edit';
  initialValues?: Partial<BidProject>;
  onOk: (values: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
}

function ProjectFormModal({ open, mode, initialValues, onOk, onCancel }: ProjectFormProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [tenderOptions, setTenderOptions] = useState<{ value: number; label: string }[]>([]);
  const [userOptions, setUserOptions] = useState<{ value: number; label: string }[]>([]);

  useEffect(() => {
    if (!open) return;
    form.resetFields();
    if (initialValues) {
      form.setFieldsValue({
        ...initialValues,
        deadline: initialValues.deadline ? dayjs(initialValues.deadline) : undefined,
      });
    }
  }, [open, initialValues, form]);

  useEffect(() => {
    if (!open) return;
    getTenderList({ page: 1, page_size: 200 })
      .then((res) => {
        setTenderOptions(res.data.items.map((t: Tender) => ({ value: t.id, label: t.title })));
      })
      .catch(() => {});
    getUserList({ page: 1, page_size: 200 })
      .then((res) => {
        setUserOptions(res.data.items.map((u: SystemUser) => ({ value: u.id, label: u.real_name })));
      })
      .catch(() => {});
  }, [open]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      if (values.deadline) {
        values.deadline = values.deadline.format('YYYY-MM-DD');
      }
      setLoading(true);
      await onOk(values);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={mode === 'create' ? '新增标书项目' : '编辑标书项目'}
      open={open}
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={loading}
      width={620}
      okText={mode === 'create' ? '创建' : '保存'}
      destroyOnClose
    >
      <Form form={form} layout="vertical" style={{ maxHeight: '65vh', overflowY: 'auto', paddingRight: 8 }}>
        <Form.Item name="title" label="标书标题" rules={[{ required: true, message: '请输入标书标题' }]}>
          <Input placeholder="请输入标书标题" />
        </Form.Item>

        <Form.Item name="tender_id" label="关联招标项目">
          <Select
            placeholder="选择关联招标项目"
            showSearch
            optionFilterProp="label"
            options={tenderOptions}
            allowClear
          />
        </Form.Item>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="doc_type" label="文档类型">
              <Select placeholder="请选择文档类型" allowClear options={DOC_TYPE_OPTIONS} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="deadline" label="截止时间">
              <DatePicker style={{ width: '100%' }} placeholder="选择截止时间" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="leader_id" label="负责人">
          <Select
            placeholder="选择负责人"
            showSearch
            optionFilterProp="label"
            options={userOptions}
            allowClear
          />
        </Form.Item>

        <Form.Item name="remark" label="备注">
          <Input.TextArea rows={3} placeholder="备注信息" />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ── 主页面 ────────────────────────────────────────────────────
export default function BidListPage() {
  const navigate = useNavigate();
  const [filterForm] = Form.useForm();

  const [data, setData] = useState<BidProject[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<BidProject | null>(null);

  const loadData = useCallback(async (currentPage = page) => {
    setLoading(true);
    try {
      const values = filterForm.getFieldsValue();
      const params: Record<string, unknown> = { page: currentPage, page_size: 12 };
      if (values.keyword) params.keyword = values.keyword;
      if (values.status) params.status = values.status;

      const res = await getBidProjectList(params);
      setData(res.data.items);
      setTotal(res.data.total);
    } finally {
      setLoading(false);
    }
  }, [filterForm, page]);

  useEffect(() => {
    loadData(page);
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = () => { setPage(1); loadData(1); };
  const handleReset = () => { filterForm.resetFields(); setPage(1); loadData(1); };

  const handleCreate = async (values: Record<string, unknown>) => {
    await createBidProject(values);
    message.success('创建成功');
    setCreateOpen(false);
    loadData(1);
  };

  const handleEdit = async (values: Record<string, unknown>) => {
    if (!currentRecord) return;
    await updateBidProject(currentRecord.id, values);
    message.success('更新成功');
    setEditOpen(false);
    loadData(page);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteBidProject(id);
      message.success('删除成功');
      loadData(page);
    } catch {
      message.error('删除失败');
    }
  };

  const openEdit = (r: BidProject) => {
    setCurrentRecord(r);
    setEditOpen(true);
  };

  const statusInfo = (status: string) => STATUS_MAP[status] || { color: 'default', label: status };

  const isDeadlineClose = (deadline?: string) => {
    if (!deadline) return false;
    const days = dayjs(deadline).diff(dayjs(), 'day');
    return days >= 0 && days <= 7;
  };

  return (
    <div>
      {/* 筛选栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Form form={filterForm} layout="inline">
          <Row gutter={[12, 12]} style={{ width: '100%' }}>
            <Col span={8}>
              <Form.Item name="keyword" style={{ margin: 0 }}>
                <Input placeholder="搜索标书标题" prefix={<SearchOutlined />} allowClear />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="status" style={{ margin: 0 }}>
                <Select
                  placeholder="状态"
                  allowClear
                  style={{ width: '100%' }}
                  options={STATUS_OPTIONS}
                />
              </Form.Item>
            </Col>
            <Col span={10} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}
                style={{ background: 'linear-gradient(135deg, #0d9488, #14b8a6)', border: 'none' }}>
                查询
              </Button>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>重置</Button>
            </Col>
          </Row>
        </Form>
      </Card>

      {/* 工具栏 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={{ color: '#64748b' }}>共 {total} 个标书项目</Text>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateOpen(true)}
          style={{ background: 'linear-gradient(135deg, #0d9488, #14b8a6)', border: 'none' }}
        >
          新增标书
        </Button>
      </div>

      {/* 卡片网格 */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" />
        </div>
      ) : data.length === 0 ? (
        <Card>
          <Empty description="暂无标书项目，点击右上角新增" />
        </Card>
      ) : (
        <>
          <Row gutter={[16, 16]}>
            {data.map((project) => {
              const si = statusInfo(project.status);
              const docLabel = DOC_TYPE_OPTIONS.find(d => d.value === project.doc_type)?.label;
              const deadlineWarning = isDeadlineClose(project.deadline);

              return (
                <Col key={project.id} xs={24} sm={12} lg={8} xl={6}>
                  <Card
                    hoverable
                    style={{
                      borderRadius: 12,
                      border: '1px solid #e2e8f0',
                      boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
                    }}
                    bodyStyle={{ padding: '16px 20px' }}
                    actions={[
                      <Button
                        key="enter"
                        type="primary"
                        size="small"
                        icon={<ArrowRightOutlined />}
                        onClick={() => navigate(`/bid/${project.id}`)}
                        style={{ background: 'linear-gradient(135deg, #0d9488, #14b8a6)', border: 'none' }}
                      >
                        进入工作台
                      </Button>,
                      <Button
                        key="edit"
                        type="text"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => openEdit(project)}
                      >
                        编辑
                      </Button>,
                      <Popconfirm
                        key="delete"
                        title="确定删除该标书项目？"
                        onConfirm={() => handleDelete(project.id)}
                      >
                        <Button type="text" size="small" danger icon={<DeleteOutlined />}>
                          删除
                        </Button>
                      </Popconfirm>,
                    ]}
                  >
                    {/* 标题行 */}
                    <div style={{ marginBottom: 10 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                        <Text strong style={{ fontSize: 14, lineHeight: 1.5, flex: 1 }} ellipsis={{ tooltip: project.title }}>
                          {project.title}
                        </Text>
                        <Tag color={si.color} style={{ flexShrink: 0 }}>{si.label}</Tag>
                      </div>
                    </div>

                    {/* 标签行 */}
                    <div style={{ marginBottom: 10, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {docLabel && (
                        <Tag icon={<FileTextOutlined />} color="cyan">{docLabel}</Tag>
                      )}
                      <Tag color="blue">{project.section_count} 章节</Tag>
                    </div>

                    {/* 关联招标 */}
                    {project.tender_title && (
                      <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <FileTextOutlined style={{ color: '#94a3b8', fontSize: 12 }} />
                        <Text type="secondary" style={{ fontSize: 12 }} ellipsis={{ tooltip: project.tender_title }}>
                          {project.tender_title}
                        </Text>
                      </div>
                    )}

                    {/* 截止时间 */}
                    {project.deadline && (
                      <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <CalendarOutlined style={{ color: deadlineWarning ? '#f59e0b' : '#94a3b8', fontSize: 12 }} />
                        <Text
                          style={{ fontSize: 12, color: deadlineWarning ? '#f59e0b' : '#64748b' }}
                        >
                          截止：{dayjs(project.deadline).format('YYYY-MM-DD')}
                          {deadlineWarning && ' (即将到期)'}
                        </Text>
                      </div>
                    )}

                    {/* 负责人 */}
                    {project.leader_name && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Avatar size={16} icon={<UserOutlined />} style={{ background: '#0d9488' }} />
                        <Text type="secondary" style={{ fontSize: 12 }}>{project.leader_name}</Text>
                      </div>
                    )}
                  </Card>
                </Col>
              );
            })}
          </Row>

          {/* 分页 */}
          {total > 12 && (
            <div style={{ textAlign: 'center', marginTop: 24 }}>
              <Space>
                <Button disabled={page === 1} onClick={() => setPage(p => p - 1)}>上一页</Button>
                <Text type="secondary">第 {page} 页 / 共 {Math.ceil(total / 12)} 页</Text>
                <Button disabled={page >= Math.ceil(total / 12)} onClick={() => setPage(p => p + 1)}>下一页</Button>
              </Space>
            </div>
          )}
        </>
      )}

      {/* 新增 Modal */}
      <ProjectFormModal
        open={createOpen}
        mode="create"
        onOk={handleCreate}
        onCancel={() => setCreateOpen(false)}
      />

      {/* 编辑 Modal */}
      <ProjectFormModal
        open={editOpen}
        mode="edit"
        initialValues={currentRecord ?? undefined}
        onOk={handleEdit}
        onCancel={() => setEditOpen(false)}
      />
    </div>
  );
}
