import { useEffect, useState, useCallback } from 'react';
import {
  Card, List, Table, Button, Modal, Form, Input, Switch, InputNumber,
  Space, Tag, message, Popconfirm, Empty, Typography,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, BookOutlined } from '@ant-design/icons';
import {
  getDictTypeList, createDictType, updateDictType, deleteDictType,
  getDictItemList, createDictItem, updateDictItem, deleteDictItem,
} from '@/services/system';

const { Text } = Typography;

export default function DictPage() {
  const [types, setTypes] = useState<DictType[]>([]);
  const [typesLoading, setTypesLoading] = useState(false);
  const [selectedType, setSelectedType] = useState<DictType | null>(null);
  const [typeModalOpen, setTypeModalOpen] = useState(false);
  const [editingType, setEditingType] = useState<DictType | null>(null);
  const [typeForm] = Form.useForm();

  const [items, setItems] = useState<DictItem[]>([]);
  const [itemsLoading, setItemsLoading] = useState(false);
  const [itemModalOpen, setItemModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<DictItem | null>(null);
  const [itemForm] = Form.useForm();

  const loadTypes = useCallback(async () => {
    setTypesLoading(true);
    try {
      const res = await getDictTypeList({ page: 1, page_size: 100 });
      setTypes(res.data.items);
    } finally {
      setTypesLoading(false);
    }
  }, []);

  const loadItems = useCallback(async (typeId: number) => {
    setItemsLoading(true);
    try {
      const res = await getDictItemList(typeId);
      setItems(res.data);
    } finally {
      setItemsLoading(false);
    }
  }, []);

  useEffect(() => { loadTypes(); }, [loadTypes]);

  useEffect(() => {
    if (selectedType) { loadItems(selectedType.id); } else { setItems([]); }
  }, [selectedType, loadItems]);

  // 字典类型操作
  const handleCreateType = () => {
    setEditingType(null);
    typeForm.resetFields();
    typeForm.setFieldsValue({ status: true });
    setTypeModalOpen(true);
  };
  const handleEditType = (t: DictType) => {
    setEditingType(t);
    typeForm.setFieldsValue({ ...t, status: t.status === 1 });
    setTypeModalOpen(true);
  };
  const handleTypeSubmit = async () => {
    const values = await typeForm.validateFields();
    const data = { ...values, status: values.status ? 1 : 0 };
    if (editingType) {
      await updateDictType(editingType.id, data);
      message.success('更新成功');
    } else {
      await createDictType(data);
      message.success('创建成功');
    }
    setTypeModalOpen(false);
    loadTypes();
  };
  const handleDeleteType = async (id: number) => {
    try {
      await deleteDictType(id);
      message.success('删除成功');
      if (selectedType?.id === id) setSelectedType(null);
      loadTypes();
    } catch { /* handled by interceptor */ }
  };

  // 字典项操作
  const handleCreateItem = () => {
    setEditingItem(null);
    itemForm.resetFields();
    itemForm.setFieldsValue({ status: true, sort_order: 0 });
    setItemModalOpen(true);
  };
  const handleEditItem = (item: DictItem) => {
    setEditingItem(item);
    itemForm.setFieldsValue({ ...item, status: item.status === 1 });
    setItemModalOpen(true);
  };
  const handleItemSubmit = async () => {
    if (!selectedType) return;
    const values = await itemForm.validateFields();
    const data = { ...values, status: values.status ? 1 : 0 };
    if (editingItem) {
      await updateDictItem(editingItem.id, data);
      message.success('更新成功');
    } else {
      await createDictItem(selectedType.id, data);
      message.success('创建成功');
    }
    setItemModalOpen(false);
    loadItems(selectedType.id);
  };
  const handleDeleteItem = async (id: number) => {
    if (!selectedType) return;
    await deleteDictItem(id);
    message.success('删除成功');
    loadItems(selectedType.id);
  };

  const itemColumns = [
    { title: '显示标签', dataIndex: 'item_label', key: 'item_label' },
    {
      title: '存储值', dataIndex: 'item_value', key: 'item_value',
      render: (v: string) => <code style={{ background: '#f1f5f9', padding: '2px 8px', borderRadius: 4, fontSize: 13 }}>{v}</code>,
    },
    { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 80, align: 'center' as const },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: number) => v === 1 ? <Tag color="success">启用</Tag> : <Tag color="default">停用</Tag>,
    },
    {
      title: '操作', key: 'action', width: 120,
      render: (_: unknown, record: DictItem) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEditItem(record)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDeleteItem(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
      <Card
        title="字典类型"
        extra={<Button type="primary" size="small" icon={<PlusOutlined />} onClick={handleCreateType}>新增</Button>}
        style={{ width: 280, flexShrink: 0 }}
        styles={{ body: { padding: 0 } }}
      >
        <List
          loading={typesLoading}
          dataSource={types}
          renderItem={(t) => (
            <List.Item
              onClick={() => setSelectedType(t)}
              style={{
                padding: '12px 16px',
                cursor: 'pointer',
                borderLeft: selectedType?.id === t.id ? '3px solid #0d9488' : '3px solid transparent',
                background: selectedType?.id === t.id ? 'rgba(13,148,136,0.06)' : 'transparent',
                transition: 'all 0.2s',
              }}
              actions={[
                <Button key="edit" type="link" size="small" icon={<EditOutlined />} onClick={(e) => { e.stopPropagation(); handleEditType(t); }} />,
                <Popconfirm key="del" title="确定删除？" onConfirm={(e) => { e?.stopPropagation(); handleDeleteType(t.id); }}>
                  <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta
                avatar={<BookOutlined style={{ color: '#0d9488', fontSize: 16 }} />}
                title={<Text style={{ fontSize: 13 }}>{t.dict_name}</Text>}
                description={<Text type="secondary" style={{ fontSize: 12 }}>{t.dict_code}</Text>}
              />
            </List.Item>
          )}
        />
      </Card>

      <Card
        title={selectedType ? `${selectedType.dict_name} 字典项` : '字典项'}
        extra={selectedType && <Button type="primary" size="small" icon={<PlusOutlined />} onClick={handleCreateItem}>新增</Button>}
        style={{ flex: 1 }}
      >
        {selectedType ? (
          <Table dataSource={items} columns={itemColumns} rowKey="id" loading={itemsLoading} pagination={false} size="middle" />
        ) : (
          <Empty description="请在左侧选择一个字典类型" style={{ padding: '60px 0' }} />
        )}
      </Card>

      <Modal title={editingType ? '编辑字典类型' : '新增字典类型'} open={typeModalOpen} onCancel={() => setTypeModalOpen(false)} onOk={handleTypeSubmit} destroyOnClose>
        <Form form={typeForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="dict_name" label="类型名称" rules={[{ required: true, message: '请输入类型名称' }]}>
            <Input placeholder="如：招标方式" />
          </Form.Item>
          <Form.Item name="dict_code" label="类型编码" rules={[{ required: true, message: '请输入类型编码' }]}>
            <Input placeholder="如：tender_method" disabled={!!editingType} />
          </Form.Item>
          <Form.Item name="status" label="状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="停用" />
          </Form.Item>
          <Form.Item name="description" label="备注">
            <Input.TextArea rows={2} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title={editingItem ? '编辑字典项' : '新增字典项'} open={itemModalOpen} onCancel={() => setItemModalOpen(false)} onOk={handleItemSubmit} destroyOnClose>
        <Form form={itemForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="item_label" label="显示标签" rules={[{ required: true, message: '请输入显示标签' }]}>
            <Input placeholder="如：公开招标" />
          </Form.Item>
          <Form.Item name="item_value" label="存储值" rules={[{ required: true, message: '请输入存储值' }]}>
            <Input placeholder="如：PUBLIC" disabled={!!editingItem} />
          </Form.Item>
          <Form.Item name="sort_order" label="排序号">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="status" label="状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="停用" />
          </Form.Item>
          <Form.Item name="description" label="备注">
            <Input.TextArea rows={2} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
