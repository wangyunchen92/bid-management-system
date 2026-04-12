import { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, InputNumber, DatePicker,
  Space, message, Popconfirm, Upload, Typography, Spin,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, UploadOutlined, FileOutlined, InboxOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  getAchievementList,
  createAchievement,
  updateAchievement,
  deleteAchievement,
  uploadLibraryFile,
  getFileUrl,
  recognizeLibraryFile,
} from '@/services/library';

const { Text } = Typography;

export default function AchievementPage() {
  const [data, setData] = useState<Achievement[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Achievement | null>(null);
  const [form] = Form.useForm();
  const [recognizing, setRecognizing] = useState(false);
  const [recognizedFilePath, setRecognizedFilePath] = useState<string | null>(null);

  const load = useCallback(async (p = page, kw = keyword) => {
    setLoading(true);
    try {
      const res = await getAchievementList({ page: p, page_size: 10, keyword: kw || undefined });
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
    setModalOpen(true);
  };

  const handleEdit = (record: Achievement) => {
    setEditing(record);
    form.setFieldsValue({
      ...record,
      completion_date: record.completion_date ? dayjs(record.completion_date) : undefined,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    const payload: Record<string, unknown> = {
      ...values,
      completion_date: values.completion_date ? values.completion_date.format('YYYY-MM-DD') : undefined,
    };
    if (!editing && recognizedFilePath) {
      payload.file_path = recognizedFilePath;
    }
    if (editing) {
      await updateAchievement(editing.id, payload);
      message.success('更新成功');
    } else {
      await createAchievement(payload);
      message.success('创建成功');
    }
    setModalOpen(false);
    load(page, keyword);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteAchievement(id);
      message.success('删除成功');
      load(page, keyword);
    } catch { /* handled */ }
  };

  const columns = [
    { title: '项目名称', dataIndex: 'project_name', key: 'project_name', ellipsis: true },
    { title: '甲方', dataIndex: 'client_name', key: 'client_name', ellipsis: true, width: 160 },
    {
      title: '合同金额(万元)', dataIndex: 'contract_amount', key: 'contract_amount', width: 140, align: 'right' as const,
      render: (v?: number) => v != null ? v.toFixed(4) : '-',
    },
    { title: '完成时间', dataIndex: 'completion_date', key: 'completion_date', width: 120 },
    { title: '项目类型', dataIndex: 'project_type', key: 'project_type', width: 120 },
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
      render: (_: unknown, record: Achievement) => (
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
      title="业绩案例"
      extra={
        <Space>
          <Input
            placeholder="搜索项目名称"
            prefix={<SearchOutlined />}
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
            onPressEnter={handleSearch}
            allowClear
            style={{ width: 220 }}
          />
          <Button onClick={handleSearch}>搜索</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>新增案例</Button>
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
        title={editing ? '编辑案例' : '新增案例'}
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
                    const res = await recognizeLibraryFile('achievements', file);
                    const { recognized_fields, file_path } = res.data;
                    if (recognized_fields.error) {
                      message.warning(`AI 识别未成功：${recognized_fields.error}，请手动填写`);
                    } else {
                      const formValues: Record<string, unknown> = { ...recognized_fields };
                      if (formValues.completion_date) formValues.completion_date = dayjs(formValues.completion_date as string);
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
          <Form.Item name="project_name" label="项目名称" rules={[{ required: true, message: '请输入项目名称' }]}>
            <Input placeholder="请输入项目名称" />
          </Form.Item>
          <Form.Item name="client_name" label="甲方">
            <Input placeholder="请输入甲方名称" />
          </Form.Item>
          <Form.Item name="contract_amount" label="合同金额(万元)">
            <InputNumber
              precision={4}
              min={0}
              style={{ width: '100%' }}
              placeholder="请输入合同金额"
            />
          </Form.Item>
          <Form.Item name="completion_date" label="完成时间">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="project_type" label="项目类型">
            <Input placeholder="如：IT系统、工程建设、广告印刷" />
          </Form.Item>
          <Form.Item name="description" label="项目简介">
            <Input.TextArea rows={3} placeholder="简要描述项目背景和亮点" />
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
                    await uploadLibraryFile('achievements', editing.id, file);
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
