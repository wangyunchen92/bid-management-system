import { useEffect, useState, useCallback } from 'react';
import {
  Card, Tree, Table, Button, Modal, Form, Input, Select, TreeSelect,
  Space, Tag, message, Popconfirm, Typography,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, KeyOutlined, SearchOutlined,
} from '@ant-design/icons';
import type { TreeProps } from 'antd';
import {
  getDepartmentTree, getUserList, createUser, updateUser, deleteUser, resetUserPassword,
} from '@/services/system';

const { Text } = Typography;

function flattenDepts(depts: Department[]): { value: number; title: string }[] {
  const result: { value: number; title: string }[] = [];
  const walk = (list: Department[]) => {
    for (const d of list) {
      result.push({ value: d.id, title: d.dept_name });
      if (d.children?.length) walk(d.children);
    }
  };
  walk(depts);
  return result;
}

function toTreeData(depts: Department[]): TreeProps['treeData'] {
  return depts.map((d) => ({
    key: d.id,
    title: d.dept_name,
    children: d.children?.length ? toTreeData(d.children) : undefined,
  }));
}

export default function UserPage() {
  const [deptTree, setDeptTree] = useState<Department[]>([]);
  const [selectedDeptId, setSelectedDeptId] = useState<number | undefined>();
  const [users, setUsers] = useState<SystemUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState<number | undefined>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<SystemUser | null>(null);
  const [form] = Form.useForm();

  const loadDeptTree = useCallback(async () => {
    const res = await getDepartmentTree();
    setDeptTree(res.data);
  }, []);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (selectedDeptId) params.dept_id = selectedDeptId;
      if (keyword) params.keyword = keyword;
      if (statusFilter !== undefined) params.status = statusFilter;
      const res = await getUserList(params);
      setUsers(res.data.items);
      setTotal(res.data.total);
    } finally {
      setLoading(false);
    }
  }, [page, selectedDeptId, keyword, statusFilter]);

  useEffect(() => { loadDeptTree(); }, [loadDeptTree]);
  useEffect(() => { loadUsers(); }, [loadUsers]);

  const handleDeptSelect: TreeProps['onSelect'] = (keys) => {
    setSelectedDeptId(keys.length > 0 ? (keys[0] as number) : undefined);
    setPage(1);
  };

  const handleCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ status: 1, role: 'USER', dept_id: selectedDeptId });
    setModalOpen(true);
  };

  const handleEdit = (user: SystemUser) => {
    setEditing(user);
    form.setFieldsValue(user);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    if (editing) {
      const { username: _u, password: _p, ...updateData } = values;
      await updateUser(editing.id, updateData);
      message.success('更新成功');
    } else {
      await createUser(values);
      message.success('创建成功');
    }
    setModalOpen(false);
    loadUsers();
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteUser(id);
      message.success('删除成功');
      loadUsers();
    } catch { /* handled */ }
  };

  const handleResetPwd = async (id: number) => {
    await resetUserPassword(id);
    message.success('密码已重置为 123456');
  };

  const deptSelectData = flattenDepts(deptTree);

  const columns = [
    { title: '用户名', dataIndex: 'username', key: 'username', width: 120 },
    { title: '姓名', dataIndex: 'real_name', key: 'real_name', width: 100 },
    { title: '手机', dataIndex: 'phone', key: 'phone', width: 130 },
    { title: '部门', dataIndex: 'dept_name', key: 'dept_name', width: 120,
      render: (v: string) => v || <Text type="secondary">-</Text>,
    },
    { title: '岗位', dataIndex: 'position', key: 'position', width: 100,
      render: (v: string) => v || <Text type="secondary">-</Text>,
    },
    { title: '角色', dataIndex: 'role', key: 'role', width: 120,
      render: (v: string) => v === 'SUPER_ADMIN' ? <Tag color="red">超级管理员</Tag> : <Tag>普通用户</Tag>,
    },
    { title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: number) => v === 1 ? <Tag color="success">启用</Tag> : <Tag color="default">停用</Tag>,
    },
    {
      title: '操作', key: 'action', width: 160,
      render: (_: unknown, record: SystemUser) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="重置密码为 123456？" onConfirm={() => handleResetPwd(record.id)}>
            <Button type="link" size="small" icon={<KeyOutlined />} />
          </Popconfirm>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
      {/* 左侧部门树 */}
      <Card title="部门" style={{ width: 240, flexShrink: 0 }} styles={{ body: { padding: '8px 0' } }}>
        <Tree
          treeData={toTreeData(deptTree)}
          defaultExpandAll
          onSelect={handleDeptSelect}
          selectedKeys={selectedDeptId ? [selectedDeptId] : []}
          blockNode
        />
      </Card>

      {/* 右侧用户表格 */}
      <Card
        title="用户管理"
        extra={<Button type="primary" size="small" icon={<PlusOutlined />} onClick={handleCreate}>新增</Button>}
        style={{ flex: 1 }}
      >
        {/* 搜索栏 */}
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder="姓名/手机号"
            prefix={<SearchOutlined />}
            allowClear
            style={{ width: 200 }}
            value={keyword}
            onChange={(e) => { setKeyword(e.target.value); setPage(1); }}
          />
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 120 }}
            value={statusFilter}
            onChange={(v) => { setStatusFilter(v); setPage(1); }}
            options={[
              { label: '启用', value: 1 },
              { label: '停用', value: 0 },
            ]}
          />
        </Space>

        <Table
          dataSource={users}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="middle"
          pagination={{
            current: page,
            total,
            pageSize: 20,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p) => setPage(p),
          }}
        />
      </Card>

      {/* 用户弹窗 */}
      <Modal
        title={editing ? '编辑用户' : '新增用户'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        destroyOnClose
        width={520}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input placeholder="登录用户名" disabled={!!editing} />
          </Form.Item>
          {!editing && (
            <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password placeholder="至少6位" />
            </Form.Item>
          )}
          <Form.Item name="real_name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}>
            <Input placeholder="真实姓名" />
          </Form.Item>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Form.Item name="phone" label="手机号">
              <Input placeholder="手机号" />
            </Form.Item>
            <Form.Item name="email" label="邮箱">
              <Input placeholder="邮箱" />
            </Form.Item>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Form.Item name="dept_id" label="部门">
              <TreeSelect
                treeData={deptSelectData}
                placeholder="选择部门"
                allowClear
                treeDefaultExpandAll
              />
            </Form.Item>
            <Form.Item name="position" label="岗位">
              <Input placeholder="如：投标专员" />
            </Form.Item>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Form.Item name="role" label="角色">
              <Select options={[
                { label: '超级管理员', value: 'SUPER_ADMIN' },
                { label: '普通用户', value: 'USER' },
              ]} />
            </Form.Item>
            <Form.Item name="status" label="状态">
              <Select options={[
                { label: '启用', value: 1 },
                { label: '停用', value: 0 },
              ]} />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </div>
  );
}
