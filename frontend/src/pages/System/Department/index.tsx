import { useEffect, useState, useCallback } from 'react';
import {
  Card, Tree, Button, Modal, Form, Input, InputNumber, Switch, TreeSelect,
  Descriptions, Space, Tag, message, Popconfirm, Empty, Typography,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
} from '@ant-design/icons';
import type { TreeProps } from 'antd';
import {
  getDepartmentTree, createDepartment, updateDepartment, deleteDepartment,
} from '@/services/system';

const { Text: _Text } = Typography;

function toTreeData(depts: Department[]): TreeProps['treeData'] {
  return depts.map((d) => ({
    key: d.id,
    title: (
      <Space size={4}>
        <span>{d.dept_name}</span>
        {d.status === 0 && <Tag color="default" style={{ fontSize: 11 }}>停用</Tag>}
      </Space>
    ),
    children: d.children?.length ? toTreeData(d.children) : undefined,
  }));
}

function flattenDepts(depts: Department[]): Department[] {
  const result: Department[] = [];
  const walk = (list: Department[]) => {
    for (const d of list) {
      result.push(d);
      if (d.children?.length) walk(d.children);
    }
  };
  walk(depts);
  return result;
}

export default function DepartmentPage() {
  const [tree, setTree] = useState<Department[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Department | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Department | null>(null);
  const [form] = Form.useForm();

  const loadTree = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getDepartmentTree();
      setTree(res.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadTree(); }, [loadTree]);

  const handleSelect: TreeProps['onSelect'] = (keys) => {
    if (keys.length === 0) { setSelected(null); return; }
    const id = keys[0] as number;
    const all = flattenDepts(tree);
    setSelected(all.find((d) => d.id === id) || null);
  };

  const handleCreate = (parentId?: number) => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ parent_id: parentId, status: true, sort_order: 0 });
    setModalOpen(true);
  };

  const handleEdit = (dept: Department) => {
    setEditing(dept);
    form.setFieldsValue({ ...dept, status: dept.status === 1 });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    const data = { ...values, status: values.status ? 1 : 0, parent_id: values.parent_id || null };
    if (editing) {
      await updateDepartment(editing.id, data);
      message.success('更新成功');
    } else {
      await createDepartment(data);
      message.success('创建成功');
    }
    setModalOpen(false);
    setSelected(null);
    loadTree();
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteDepartment(id);
      message.success('删除成功');
      if (selected?.id === id) setSelected(null);
      loadTree();
    } catch { /* handled by interceptor */ }
  };

  const treeSelectData = flattenDepts(tree).map((d) => ({
    value: d.id,
    title: d.dept_name,
    key: d.id,
  }));

  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
      {/* 左侧：部门树 */}
      <Card
        title="组织架构"
        extra={<Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => handleCreate()}>新增</Button>}
        style={{ width: 300, flexShrink: 0 }}
        loading={loading}
      >
        {tree.length > 0 ? (
          <Tree
            treeData={toTreeData(tree)}
            defaultExpandAll
            onSelect={handleSelect}
            selectedKeys={selected ? [selected.id] : []}
            blockNode
          />
        ) : (
          <Empty description="暂无部门" />
        )}
      </Card>

      {/* 右侧：部门详情 */}
      <Card title={selected ? selected.dept_name : '部门详情'} style={{ flex: 1 }}>
        {selected ? (
          <div>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="部门名称">{selected.dept_name}</Descriptions.Item>
              <Descriptions.Item label="部门编码"><code>{selected.dept_code}</code></Descriptions.Item>
              <Descriptions.Item label="排序号">{selected.sort_order}</Descriptions.Item>
              <Descriptions.Item label="状态">
                {selected.status === 1 ? <Tag color="success">启用</Tag> : <Tag color="default">停用</Tag>}
              </Descriptions.Item>
            </Descriptions>
            <Space style={{ marginTop: 16 }}>
              <Button icon={<PlusOutlined />} onClick={() => handleCreate(selected.id)}>新增子部门</Button>
              <Button icon={<EditOutlined />} onClick={() => handleEdit(selected)}>编辑</Button>
              <Popconfirm title="确定删除此部门？" onConfirm={() => handleDelete(selected.id)}>
                <Button danger icon={<DeleteOutlined />}>删除</Button>
              </Popconfirm>
            </Space>
          </div>
        ) : (
          <Empty description="请在左侧选择一个部门" style={{ padding: '60px 0' }} />
        )}
      </Card>

      {/* 弹窗 */}
      <Modal
        title={editing ? '编辑部门' : '新增部门'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="dept_name" label="部门名称" rules={[{ required: true, message: '请输入部门名称' }]}>
            <Input placeholder="如：经营部" />
          </Form.Item>
          <Form.Item name="dept_code" label="部门编码" rules={[{ required: true, message: '请输入部门编码' }]}>
            <Input placeholder="如：BIZ" disabled={!!editing} />
          </Form.Item>
          <Form.Item name="parent_id" label="上级部门">
            <TreeSelect
              treeData={treeSelectData}
              placeholder="留空为顶级部门"
              allowClear
              treeDefaultExpandAll
            />
          </Form.Item>
          <Form.Item name="sort_order" label="排序号">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="status" label="状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="停用" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
