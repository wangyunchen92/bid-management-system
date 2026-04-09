import { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, DatePicker, Switch,
  Space, Tag, message, Popconfirm,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  getPersonnelCertList,
  createPersonnelCert,
  updatePersonnelCert,
  deletePersonnelCert,
} from '@/services/library';

export default function PersonnelCertPage() {
  const [data, setData] = useState<PersonnelCert[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<PersonnelCert | null>(null);
  const [form] = Form.useForm();

  const load = useCallback(async (p = page, kw = keyword) => {
    setLoading(true);
    try {
      const res = await getPersonnelCertList({ page: p, page_size: 10, keyword: kw || undefined });
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
    form.setFieldsValue({ status: true });
    setModalOpen(true);
  };

  const handleEdit = (record: PersonnelCert) => {
    setEditing(record);
    form.setFieldsValue({
      ...record,
      status: record.status === 1,
      issue_date: record.issue_date ? dayjs(record.issue_date) : undefined,
      expiry_date: record.expiry_date ? dayjs(record.expiry_date) : undefined,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    const payload = {
      ...values,
      status: values.status ? 1 : 0,
      issue_date: values.issue_date ? values.issue_date.format('YYYY-MM-DD') : undefined,
      expiry_date: values.expiry_date ? values.expiry_date.format('YYYY-MM-DD') : undefined,
    };
    if (editing) {
      await updatePersonnelCert(editing.id, payload);
      message.success('更新成功');
    } else {
      await createPersonnelCert(payload);
      message.success('创建成功');
    }
    setModalOpen(false);
    load(page, keyword);
  };

  const handleDelete = async (id: number) => {
    try {
      await deletePersonnelCert(id);
      message.success('删除成功');
      load(page, keyword);
    } catch { /* handled */ }
  };

  const now = dayjs();
  const columns = [
    { title: '人员姓名', dataIndex: 'person_name', key: 'person_name', width: 100 },
    { title: '证书名称', dataIndex: 'cert_name', key: 'cert_name', ellipsis: true },
    {
      title: '证书编号', dataIndex: 'cert_no', key: 'cert_no', width: 160,
      render: (v?: string) => v ? <code style={{ background: '#f1f5f9', padding: '2px 8px', borderRadius: 4, fontSize: 12 }}>{v}</code> : '-',
    },
    { title: '证书类型', dataIndex: 'cert_type', key: 'cert_type', width: 120 },
    { title: '有效期', dataIndex: 'expiry_date', key: 'expiry_date', width: 120 },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: number, r: PersonnelCert) => {
        if (v !== 1) return <Tag color="default">停用</Tag>;
        const expired = r.expiry_date && dayjs(r.expiry_date).isBefore(now);
        return expired ? <Tag color="error">已过期</Tag> : <Tag color="success">有效</Tag>;
      },
    },
    {
      title: '操作', key: 'action', width: 100,
      render: (_: unknown, record: PersonnelCert) => (
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
      title="人员证书"
      extra={
        <Space>
          <Input
            placeholder="搜索人员/证书名称"
            prefix={<SearchOutlined />}
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
            onPressEnter={handleSearch}
            allowClear
            style={{ width: 220 }}
          />
          <Button onClick={handleSearch}>搜索</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>新增证书</Button>
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
        title={editing ? '编辑证书' : '新增证书'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        destroyOnHidden
        width={560}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="person_name" label="人员姓名" rules={[{ required: true, message: '请输入人员姓名' }]}>
            <Input placeholder="请输入姓名" />
          </Form.Item>
          <Form.Item name="cert_name" label="证书名称" rules={[{ required: true, message: '请输入证书名称' }]}>
            <Input placeholder="请输入证书名称" />
          </Form.Item>
          <Form.Item name="cert_no" label="证书编号">
            <Input placeholder="请输入证书编号" />
          </Form.Item>
          <Form.Item name="cert_type" label="证书类型">
            <Input placeholder="如：建造师、安全员、会计师" />
          </Form.Item>
          <Space style={{ width: '100%' }}>
            <Form.Item name="issue_date" label="发证日期" style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="expiry_date" label="有效期" style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Space>
          <Form.Item name="status" label="状态" valuePropName="checked">
            <Switch checkedChildren="有效" unCheckedChildren="停用" />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} placeholder="备注信息" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
