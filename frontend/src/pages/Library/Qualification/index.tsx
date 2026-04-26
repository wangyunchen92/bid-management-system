import { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, Select, DatePicker, Switch,
  Space, Tag, Popconfirm, Upload, Typography, Spin, App } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, UploadOutlined, FileOutlined, InboxOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  getQualificationList,
  createQualification,
  updateQualification,
  deleteQualification,
  uploadLibraryFile,
  getFileUrl,
  recognizeLibraryFile,
} from '@/services/library';

const { Text } = Typography;

const CERT_TYPES = [
  { label: '营业执照', value: 'BUSINESS_LICENSE' },
  { label: '资质证书', value: 'QUALIFICATION' },
  { label: 'ISO认证', value: 'ISO' },
  { label: '安全生产许可证', value: 'SAFETY' },
  { label: '其他', value: 'OTHER' },
];

export default function QualificationPage() {
  const { message } = App.useApp();
  const [data, setData] = useState<Qualification[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Qualification | null>(null);
  const [form] = Form.useForm();
  const [recognizing, setRecognizing] = useState(false);
  const [recognizedFilePath, setRecognizedFilePath] = useState<string | null>(null);

  const load = useCallback(async (p = page, kw = keyword) => {
    setLoading(true);
    try {
      const res = await getQualificationList({ page: p, page_size: 10, keyword: kw || undefined });
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
    setRecognizedFilePath(null);
    form.resetFields();
    form.setFieldsValue({ status: true });
    setModalOpen(true);
  };

  const handleEdit = (record: Qualification) => {
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
    const payload: Record<string, unknown> = {
      ...values,
      status: values.status ? 1 : 0,
      issue_date: values.issue_date ? values.issue_date.format('YYYY-MM-DD') : undefined,
      expiry_date: values.expiry_date ? values.expiry_date.format('YYYY-MM-DD') : undefined,
    };
    if (!editing && recognizedFilePath) {
      payload.file_path = recognizedFilePath;
    }
    if (editing) {
      await updateQualification(editing.id, payload);
      message.success('更新成功');
    } else {
      await createQualification(payload);
      message.success('创建成功');
    }
    setModalOpen(false);
    load(page, keyword);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteQualification(id);
      message.success('删除成功');
      load(page, keyword);
    } catch { /* handled */ }
  };

  const now = dayjs();
  const columns = [
    { title: '证书名称', dataIndex: 'cert_name', key: 'cert_name', ellipsis: true },
    {
      title: '证书类型', dataIndex: 'cert_type', key: 'cert_type', width: 120,
      render: (v?: string) => {
        if (!v) return '-';
        const label = CERT_TYPES.find(t => t.value === v)?.label ?? v;
        return <Tag color="blue">{label}</Tag>;
      },
    },
    {
      title: '证书编号', dataIndex: 'cert_no', key: 'cert_no', width: 160,
      render: (v?: string) => v ? <code style={{ background: '#f1f5f9', padding: '2px 8px', borderRadius: 4, fontSize: 12 }}>{v}</code> : '-',
    },
    { title: '发证机关', dataIndex: 'issuing_authority', key: 'issuing_authority', ellipsis: true },
    {
      title: '有效期', key: 'validity', width: 200,
      render: (_: unknown, r: Qualification) => {
        const start = r.issue_date || '-';
        const end = r.expiry_date || '-';
        return `${start} ~ ${end}`;
      },
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: number, r: Qualification) => {
        if (v !== 1) return <Tag color="default">停用</Tag>;
        const expired = r.expiry_date && dayjs(r.expiry_date).isBefore(now);
        return expired ? <Tag color="error">已过期</Tag> : <Tag color="success">有效</Tag>;
      },
    },
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
      render: (_: unknown, record: Qualification) => (
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
      title="资质证书"
      extra={
        <Space>
          <Input
            placeholder="搜索证书名称"
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
          {!editing && (
            <div style={{ marginBottom: 16 }}>
              <Upload.Dragger
                accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                maxCount={1}
                showUploadList={false}
                disabled={recognizing}
                beforeUpload={async (file) => {
                  setRecognizing(true);
                  try {
                    const res = await recognizeLibraryFile('qualifications', file);
                    const { recognized_fields, file_path } = res.data;
                    if (recognized_fields.error) {
                      message.warning(`AI 识别未成功：${recognized_fields.error}，请手动填写`);
                    } else {
                      const formValues: Record<string, unknown> = { ...recognized_fields };
                      if (formValues.issue_date) formValues.issue_date = dayjs(formValues.issue_date as string);
                      if (formValues.expiry_date) formValues.expiry_date = dayjs(formValues.expiry_date as string);
                      form.setFieldsValue(formValues);
                      message.success('AI 识别成功，已自动填充表单');
                    }
                    setRecognizedFilePath(file_path);
                  } catch {
                    message.error('文件上传失败');
                  } finally {
                    setRecognizing(false);
                  }
                  return false;
                }}
              >
                {recognizing ? (
                  <div style={{ padding: '12px 0' }}>
                    <Spin />
                    <div style={{ marginTop: 8, color: '#0d9488' }}>AI 正在识别中...</div>
                  </div>
                ) : (
                  <>
                    <p className="ant-upload-drag-icon">
                      <InboxOutlined style={{ color: '#0d9488' }} />
                    </p>
                    <p className="ant-upload-text" style={{ fontSize: 13 }}>
                      上传证书/资料文件，AI 自动识别填充
                    </p>
                    <p className="ant-upload-hint" style={{ fontSize: 12 }}>
                      支持 PDF、Word、图片，最大 20MB
                    </p>
                  </>
                )}
              </Upload.Dragger>
            </div>
          )}
          <Form.Item name="cert_name" label="证书名称" rules={[{ required: true, message: '请输入证书名称' }]}>
            <Input placeholder="请输入证书名称" />
          </Form.Item>
          <Form.Item name="cert_type" label="证书类型">
            <Select placeholder="请选择证书类型" options={CERT_TYPES} allowClear />
          </Form.Item>
          <Form.Item name="cert_no" label="证书编号">
            <Input placeholder="请输入证书编号" />
          </Form.Item>
          <Form.Item name="issuing_authority" label="发证机关">
            <Input placeholder="请输入发证机关" />
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
          {editing && (
            <Form.Item label="上传附件">
              <Upload
                accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                maxCount={1}
                showUploadList={false}
                beforeUpload={async (file) => {
                  try {
                    await uploadLibraryFile('qualifications', editing.id, file);
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
