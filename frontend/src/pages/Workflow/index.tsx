import { useEffect, useState, useCallback } from 'react';
import {
  Card, Tabs, Table, Button, Modal, Form, Input, Tag, Space,
  Timeline, Typography, Select,  App } from 'antd';
import {
  CheckCircleOutlined, CloseCircleOutlined, SwapOutlined,
} from '@ant-design/icons';
import {
  getMyPending, getMyInitiated, getApprovalDetail,
  approveInstance, rejectInstance, transferInstance,
} from '@/services/approval';
import { getUserList } from '@/services/system';
import dayjs from 'dayjs';

const { Text } = Typography;
const { TextArea } = Input;

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  PENDING: { color: 'processing', label: '待审批' },
  APPROVED: { color: 'success', label: '已通过' },
  REJECTED: { color: 'error', label: '已驳回' },
};

const ACTION_MAP: Record<string, { color: string; label: string }> = {
  SUBMIT: { color: 'blue', label: '发起审批' },
  APPROVE: { color: 'green', label: '同意' },
  REJECT: { color: 'red', label: '驳回' },
  TRANSFER: { color: 'orange', label: '转审' },
};

export default function WorkflowPage() {
  const { message } = App.useApp();
  const [activeTab, setActiveTab] = useState('pending');
  const [pendingList, setPendingList] = useState<ApprovalInstance[]>([]);
  const [initiatedList, setInitiatedList] = useState<ApprovalInstance[]>([]);
  const [pendingTotal, setPendingTotal] = useState(0);
  const [initiatedTotal, setInitiatedTotal] = useState(0);
  const [pendingPage, setPendingPage] = useState(1);
  const [initiatedPage, setInitiatedPage] = useState(1);
  const [loading, setLoading] = useState(false);

  // 审批操作
  const [actionModal, setActionModal] = useState<{ type: 'approve' | 'reject' | 'transfer'; id: number } | null>(null);
  const [actionForm] = Form.useForm();
  const [users, setUsers] = useState<{ value: number; label: string }[]>([]);

  // 详情
  const [detailModal, setDetailModal] = useState(false);
  const [detail, setDetail] = useState<ApprovalDetail | null>(null);

  const loadPending = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getMyPending({ page: pendingPage, page_size: 20 });
      setPendingList(res.data.items);
      setPendingTotal(res.data.total);
    } finally {
      setLoading(false);
    }
  }, [pendingPage]);

  const loadInitiated = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getMyInitiated({ page: initiatedPage, page_size: 20 });
      setInitiatedList(res.data.items);
      setInitiatedTotal(res.data.total);
    } finally {
      setLoading(false);
    }
  }, [initiatedPage]);

  useEffect(() => {
    if (activeTab === 'pending') loadPending();
    else loadInitiated();
  }, [activeTab, loadPending, loadInitiated]);

  const loadUsers = useCallback(async () => {
    const res = await getUserList({ page: 1, page_size: 100 });
    setUsers(res.data.items.map((u: SystemUser) => ({ value: u.id, label: u.real_name })));
  }, []);

  const handleAction = (type: 'approve' | 'reject' | 'transfer', id: number) => {
    actionForm.resetFields();
    if (type === 'transfer') loadUsers();
    setActionModal({ type, id });
  };

  const handleActionSubmit = async () => {
    if (!actionModal) return;
    const values = await actionForm.validateFields();
    const { type, id } = actionModal;

    if (type === 'approve') {
      await approveInstance(id, values.comment);
      message.success('已同意');
    } else if (type === 'reject') {
      await rejectInstance(id, values.comment);
      message.success('已驳回');
    } else {
      await transferInstance(id, values.to_user_id, values.comment);
      message.success('已转审');
    }
    setActionModal(null);
    loadPending();
    loadInitiated();
  };

  const handleViewDetail = async (id: number) => {
    try {
      const res = await getApprovalDetail(id);
      setDetail(res.data);
      setDetailModal(true);
    } catch { /* handled */ }
  };

  const pendingColumns = [
    { title: '标题', dataIndex: 'title', key: 'title',
      render: (v: string, r: ApprovalInstance) => <a onClick={() => handleViewDetail(r.id)}>{v}</a>,
    },
    { title: '发起人', dataIndex: 'initiator_name', key: 'initiator_name', width: 100 },
    { title: '发起时间', dataIndex: 'created_at', key: 'created_at', width: 170,
      render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '操作', key: 'action', width: 200,
      render: (_: unknown, r: ApprovalInstance) => (
        <Space>
          <Button type="primary" size="small" icon={<CheckCircleOutlined />} onClick={() => handleAction('approve', r.id)}>同意</Button>
          <Button danger size="small" icon={<CloseCircleOutlined />} onClick={() => handleAction('reject', r.id)}>驳回</Button>
          <Button size="small" icon={<SwapOutlined />} onClick={() => handleAction('transfer', r.id)}>转审</Button>
        </Space>
      ),
    },
  ];

  const initiatedColumns = [
    { title: '标题', dataIndex: 'title', key: 'title',
      render: (v: string, r: ApprovalInstance) => <a onClick={() => handleViewDetail(r.id)}>{v}</a>,
    },
    { title: '审批人', dataIndex: 'approver_name', key: 'approver_name', width: 100 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (v: string) => {
        const s = STATUS_MAP[v] || { color: 'default', label: v };
        return <Tag color={s.color}>{s.label}</Tag>;
      },
    },
    { title: '发起时间', dataIndex: 'created_at', key: 'created_at', width: 170,
      render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-',
    },
  ];

  return (
    <Card>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
        {
          key: 'pending',
          label: `我的待办 (${pendingTotal})`,
          children: (
            <Table dataSource={pendingList} columns={pendingColumns} rowKey="id" loading={loading} size="middle"
              pagination={{ current: pendingPage, total: pendingTotal, pageSize: 20, onChange: setPendingPage }} />
          ),
        },
        {
          key: 'initiated',
          label: '我发起的',
          children: (
            <Table dataSource={initiatedList} columns={initiatedColumns} rowKey="id" loading={loading} size="middle"
              pagination={{ current: initiatedPage, total: initiatedTotal, pageSize: 20, onChange: setInitiatedPage }} />
          ),
        },
      ]} />

      {/* 审批操作弹窗 */}
      <Modal
        title={actionModal?.type === 'approve' ? '同意审批' : actionModal?.type === 'reject' ? '驳回审批' : '转审'}
        open={!!actionModal}
        onCancel={() => setActionModal(null)}
        onOk={handleActionSubmit}
        destroyOnHidden
      >
        <Form form={actionForm} layout="vertical" style={{ marginTop: 16 }}>
          {actionModal?.type === 'transfer' && (
            <Form.Item name="to_user_id" label="转审人" rules={[{ required: true, message: '请选择转审人' }]}>
              <Select placeholder="选择转审人" options={users} showSearch optionFilterProp="label" />
            </Form.Item>
          )}
          <Form.Item name="comment" label="审批意见">
            <TextArea rows={3} placeholder="请输入审批意见（可选）" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 审批详情弹窗 */}
      <Modal
        title="审批详情"
        open={detailModal}
        onCancel={() => setDetailModal(false)}
        footer={null}
        width={600}
      >
        {detail && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Text strong style={{ fontSize: 16 }}>{detail.instance.title}</Text>
              <Tag color={STATUS_MAP[detail.instance.status]?.color} style={{ marginLeft: 8 }}>
                {STATUS_MAP[detail.instance.status]?.label}
              </Tag>
            </div>
            <Timeline
              items={detail.records.map((r) => ({
                color: ACTION_MAP[r.action]?.color || 'gray',
                children: (
                  <div>
                    <Space>
                      <Tag color={ACTION_MAP[r.action]?.color}>{ACTION_MAP[r.action]?.label}</Tag>
                      <Text strong>{r.operator_name}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {r.created_at ? dayjs(r.created_at).format('YYYY-MM-DD HH:mm') : ''}
                      </Text>
                    </Space>
                    {r.comment && <div style={{ marginTop: 4, color: '#475569' }}>{r.comment}</div>}
                  </div>
                ),
              }))}
            />
          </div>
        )}
      </Modal>
    </Card>
  );
}
