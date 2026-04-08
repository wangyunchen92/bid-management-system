import { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, InputNumber, Switch,
  Space, Tag, message, Popconfirm,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { getRoleList, createRole, updateRole, deleteRole } from '@/services/system';

export default function RolePage() {
  const [roles, setRoles] = useState<SysRole[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<SysRole | null>(null);
  const [form] = Form.useForm();

  const loadRoles = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getRoleList();
      setRoles(res.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadRoles(); }, [loadRoles]);

  const handleCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ status: true, sort_order: 0 });
    setModalOpen(true);
  };

  const handleEdit = (role: SysRole) => {
    setEditing(role);
    form.setFieldsValue({ ...role, status: role.status === 1 });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    const data = { ...values, status: values.status ? 1 : 0 };
    if (editing) {
      await updateRole(editing.id, data);
      message.success('更新成功');
    } else {
      await createRole(data);
      message.success('创建成功');
    }
    setModalOpen(false);
    loadRoles();
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteRole(id);
      message.success('删除成功');
      loadRoles();
    } catch { /* handled */ }
  };

  const columns = [
    { title: '角色名称', dataIndex: 'role_name', key: 'role_name' },
    {
      title: '角色编码', dataIndex: 'role_code', key: 'role_code',
      render: (v: string) => <code style={{ background: '#f1f5f9', padding: '2px 8px', borderRadius: 4, fontSize: 13 }}>{v}</code>,
    },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 80, align: 'center' as const },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: number) => v === 1 ? <Tag color="success">启用</Tag> : <Tag color="default">停用</Tag>,
    },
    {
      title: '操作', key: 'action', width: 120,
      render: (_: unknown, record: SysRole) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          {record.role_code !== 'SUPER_ADMIN' && (
            <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
              <Button type="link" size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card
      title="角色管理"
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>新增角色</Button>}
    >
      <Table dataSource={roles} columns={columns} rowKey="id" loading={loading} pagination={false} size="middle" />

      <Modal
        title={editing ? '编辑角色' : '新增角色'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="role_name" label="角色名称" rules={[{ required: true, message: '请输入角色名称' }]}>
            <Input placeholder="如：投标专员" />
          </Form.Item>
          <Form.Item name="role_code" label="角色编码" rules={[{ required: true, message: '请输入角色编码' }]}>
            <Input placeholder="如：BID_SPECIALIST" disabled={!!editing} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="角色职责描述" />
          </Form.Item>
          <Form.Item name="sort_order" label="排序号">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="status" label="状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="停用" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
