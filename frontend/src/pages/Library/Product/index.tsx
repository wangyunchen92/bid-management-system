import { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, InputNumber,
  Space, message, Popconfirm, Upload, Typography,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, UploadOutlined, FileOutlined } from '@ant-design/icons';
import {
  getProductList,
  createProduct,
  updateProduct,
  deleteProduct,
  uploadLibraryFile,
  getFileUrl,
} from '@/services/library';

const { Text } = Typography;

export default function ProductPage() {
  const [data, setData] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [form] = Form.useForm();

  const load = useCallback(async (p = page, kw = keyword) => {
    setLoading(true);
    try {
      const res = await getProductList({ page: p, page_size: 10, keyword: kw || undefined });
      setData(res.data.items);
      setTotal(res.data.total);
    } finally {
      setLoading(false);
    }
  }, [page, keyword]);

  useEffect(() => { load(); }, [load]);

  const handleSearch = () => { setPage(1); load(1, keyword); };

  const handleCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ quantity: 1 });
    setModalOpen(true);
  };

  const handleEdit = (record: Product) => {
    setEditing(record);
    form.setFieldsValue({ ...record });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    if (editing) {
      await updateProduct(editing.id, values);
      message.success('更新成功');
    } else {
      await createProduct(values);
      message.success('创建成功');
    }
    setModalOpen(false);
    load(page, keyword);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteProduct(id);
      message.success('删除成功');
      load(page, keyword);
    } catch { /* handled */ }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true },
    { title: '型号', dataIndex: 'model', key: 'model', width: 140 },
    { title: '品牌', dataIndex: 'brand', key: 'brand', width: 120 },
    {
      title: '数量', dataIndex: 'quantity', key: 'quantity', width: 80, align: 'right' as const,
      render: (v: number) => v ?? '-',
    },
    { title: '单位', dataIndex: 'unit', key: 'unit', width: 80 },
    {
      title: '附件', dataIndex: 'file_path', key: 'file_path', width: 100,
      render: (v: string) => v ? (
        <a href={getFileUrl(v)} target="_blank" rel="noopener">
          <Space size={4}><FileOutlined />查看</Space>
        </a>
      ) : <Text type="secondary">—</Text>,
    },
    {
      title: '操作', key: 'action', width: 100,
      render: (_: unknown, record: Product) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title="产品/设备"
      extra={
        <Space>
          <Input
            placeholder="搜索名称/型号"
            prefix={<SearchOutlined />}
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
            onPressEnter={handleSearch}
            allowClear
            style={{ width: 220 }}
          />
          <Button onClick={handleSearch}>搜索</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>新增产品</Button>
        </Space>
      }
    >
      <Table
        dataSource={data}
        columns={columns}
        rowKey="id"
        loading={loading}
        size="middle"
        pagination={{
          total,
          current: page,
          pageSize: 10,
          onChange: (p) => { setPage(p); load(p, keyword); },
          showTotal: t => `共 ${t} 条`,
        }}
      />

      <Modal
        title={editing ? '编辑产品' : '新增产品'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        destroyOnHidden
        width={520}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="请输入产品/设备名称" />
          </Form.Item>
          <Form.Item name="model" label="型号">
            <Input placeholder="请输入型号" />
          </Form.Item>
          <Form.Item name="brand" label="品牌">
            <Input placeholder="请输入品牌" />
          </Form.Item>
          <Space style={{ width: '100%' }}>
            <Form.Item name="quantity" label="数量" style={{ flex: 1 }} rules={[{ required: true, message: '请输入数量' }]}>
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="unit" label="单位" style={{ flex: 1 }}>
              <Input placeholder="台/套/个/件" />
            </Form.Item>
          </Space>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="产品/设备描述" />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} placeholder="备注信息" />
          </Form.Item>
          {editing && (
            <Form.Item label="上传附件">
              <Upload
                accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                maxCount={1}
                showUploadList={false}
                beforeUpload={async (file) => {
                  try {
                    await uploadLibraryFile('products', editing.id, file);
                    message.success('上传成功');
                    load(page, keyword);
                  } catch { /* handled */ }
                  return false;
                }}
              >
                <Button icon={<UploadOutlined />}>
                  {editing.file_path ? '重新上传' : '上传文件'}
                </Button>
              </Upload>
              {editing.file_path && (
                <a href={getFileUrl(editing.file_path)} target="_blank" rel="noopener" style={{ marginLeft: 8, fontSize: 12 }}>
                  当前文件
                </a>
              )}
            </Form.Item>
          )}
        </Form>
      </Modal>
    </Card>
  );
}
