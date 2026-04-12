import { useEffect, useState, useCallback } from 'react';
import {
  Button,
  Card,
  Col,
  Form,
  Input,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Tag,
  Typography,  App } from 'antd';
import { PlusOutlined, EyeOutlined, EditOutlined, DeleteOutlined, BookOutlined } from '@ant-design/icons';
import { getKnowledgeList, createKnowledge, updateKnowledge, deleteKnowledge } from '@/services/knowledge';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const CATEGORY_OPTIONS = [
  { label: '技术方案', value: 'technical' },
  { label: '商务文件', value: 'commercial' },
  { label: '资质文件', value: 'qualification' },
  { label: '报价文件', value: 'pricing' },
  { label: '项目管理', value: 'management' },
  { label: '其他', value: 'other' },
];

const CATEGORY_COLORS: Record<string, string> = {
  technical: 'blue',
  commercial: 'green',
  qualification: 'purple',
  pricing: 'orange',
  management: 'cyan',
  other: 'default',
};

function getCategoryLabel(value?: string) {
  return CATEGORY_OPTIONS.find((o) => o.value === value)?.label ?? value ?? '';
}

export default function KnowledgePage() {
  const { message } = App.useApp();
  const [list, setList] = useState<KnowledgeTemplate[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [category, setCategory] = useState<string | undefined>();

  // Modal states
  const [detailVisible, setDetailVisible] = useState(false);
  const [editVisible, setEditVisible] = useState(false);
  const [selectedItem, setSelectedItem] = useState<KnowledgeTemplate | null>(null);
  const [editingItem, setEditingItem] = useState<KnowledgeTemplate | null>(null);
  const [submitLoading, setSubmitLoading] = useState(false);

  const [form] = Form.useForm();

  const fetchList = useCallback(async (p = 1, kw = keyword, cat = category) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: 12 };
      if (kw) params.keyword = kw;
      if (cat) params.category = cat;
      const res = await getKnowledgeList(params);
      if (res.code === 200 && res.data) {
        setList(res.data.items);
        setTotal(res.data.total);
        setPage(p);
      }
    } finally {
      setLoading(false);
    }
  }, [keyword, category]);

  useEffect(() => {
    fetchList(1, keyword, category);
  }, []);

  function handleSearch() {
    fetchList(1, keyword, category);
  }

  function handleCategoryChange(val: string | undefined) {
    setCategory(val);
    fetchList(1, keyword, val);
  }

  function handleViewDetail(item: KnowledgeTemplate) {
    setSelectedItem(item);
    setDetailVisible(true);
  }

  function handleEdit(item: KnowledgeTemplate) {
    setEditingItem(item);
    form.setFieldsValue(item);
    setEditVisible(true);
  }

  function handleCreate() {
    setEditingItem(null);
    form.resetFields();
    setEditVisible(true);
  }

  async function handleDelete(id: number) {
    await deleteKnowledge(id);
    message.success('删除成功');
    fetchList(page, keyword, category);
  }

  async function handleSubmit() {
    const values = await form.validateFields();
    setSubmitLoading(true);
    try {
      if (editingItem) {
        await updateKnowledge(editingItem.id, values);
        message.success('更新成功');
      } else {
        await createKnowledge(values);
        message.success('创建成功');
      }
      setEditVisible(false);
      fetchList(1, keyword, category);
    } finally {
      setSubmitLoading(false);
    }
  }

  function parseTags(tags?: string): string[] {
    if (!tags) return [];
    return tags.split(',').map((t) => t.trim()).filter(Boolean);
  }

  return (
    <div>
      {/* Toolbar */}
      <div style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <Input.Search
          placeholder="搜索标题/内容..."
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onSearch={handleSearch}
          style={{ width: 260 }}
          allowClear
        />
        <Select
          placeholder="全部分类"
          allowClear
          style={{ width: 160 }}
          options={CATEGORY_OPTIONS}
          value={category}
          onChange={handleCategoryChange}
        />
        <div style={{ flex: 1 }} />
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新增模板
        </Button>
      </div>

      {/* Cards grid */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#94a3b8' }}>加载中...</div>
      ) : list.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 80, color: '#94a3b8' }}>
          <BookOutlined style={{ fontSize: 48, marginBottom: 12 }} />
          <div>暂无知识库模板</div>
        </div>
      ) : (
        <Row gutter={[16, 16]}>
          {list.map((item) => {
            const tagList = parseTags(item.tags);
            const summary = (item.content ?? '').slice(0, 100);
            return (
              <Col span={8} key={item.id}>
                <Card
                  hoverable
                  style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.08)', height: '100%' }}
                  actions={[
                    <EyeOutlined key="view" title="查看详情" onClick={() => handleViewDetail(item)} />,
                    <EditOutlined key="edit" title="编辑" onClick={() => handleEdit(item)} />,
                    <Popconfirm
                      key="delete"
                      title="确认删除该模板？"
                      onConfirm={() => handleDelete(item.id)}
                      okText="删除"
                      cancelText="取消"
                    >
                      <DeleteOutlined style={{ color: '#ef4444' }} title="删除" />
                    </Popconfirm>,
                  ]}
                >
                  <Space direction="vertical" style={{ width: '100%' }} size={8}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, justifyContent: 'space-between' }}>
                      <Title level={5} style={{ margin: 0, flex: 1 }} ellipsis={{ rows: 2 }}>
                        {item.title}
                      </Title>
                      {item.category && (
                        <Tag color={CATEGORY_COLORS[item.category] ?? 'default'}>
                          {getCategoryLabel(item.category)}
                        </Tag>
                      )}
                    </div>

                    {tagList.length > 0 && (
                      <div>
                        {tagList.map((t) => (
                          <Tag key={t} style={{ marginBottom: 4, fontSize: 11 }}>{t}</Tag>
                        ))}
                      </div>
                    )}

                    <Paragraph
                      style={{ color: '#64748b', fontSize: 13, margin: 0, minHeight: 40 }}
                      ellipsis={{ rows: 2 }}
                    >
                      {summary ? `${summary}${(item.content?.length ?? 0) > 100 ? '...' : ''}` : '暂无内容'}
                    </Paragraph>

                    <Text type="secondary" style={{ fontSize: 12 }}>
                      使用次数：{item.usage_count}
                      {item.created_at && `　创建于 ${item.created_at.slice(0, 10)}`}
                    </Text>
                  </Space>
                </Card>
              </Col>
            );
          })}
        </Row>
      )}

      {/* Pagination hint */}
      {total > 12 && (
        <div style={{ textAlign: 'center', marginTop: 16, color: '#94a3b8' }}>
          共 {total} 条，当前显示第 {page} 页
        </div>
      )}

      {/* Detail Modal */}
      <Modal
        title={selectedItem?.title}
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>关闭</Button>,
        ]}
        width={720}
      >
        {selectedItem && (
          <Space direction="vertical" style={{ width: '100%' }} size={12}>
            <div>
              {selectedItem.category && (
                <Tag color={CATEGORY_COLORS[selectedItem.category] ?? 'default'}>
                  {getCategoryLabel(selectedItem.category)}
                </Tag>
              )}
              {parseTags(selectedItem.tags).map((t) => (
                <Tag key={t}>{t}</Tag>
              ))}
            </div>
            <div style={{ background: '#f8fafc', borderRadius: 8, padding: 16, whiteSpace: 'pre-wrap', maxHeight: 400, overflow: 'auto', fontSize: 14, lineHeight: 1.8 }}>
              {selectedItem.content || '暂无内容'}
            </div>
            {selectedItem.remark && (
              <div>
                <Text type="secondary">备注：{selectedItem.remark}</Text>
              </div>
            )}
            <Text type="secondary" style={{ fontSize: 12 }}>
              使用次数：{selectedItem.usage_count}
              {selectedItem.created_at && `　创建于 ${selectedItem.created_at.slice(0, 10)}`}
            </Text>
          </Space>
        )}
      </Modal>

      {/* Edit/Create Modal */}
      <Modal
        title={editingItem ? '编辑模板' : '新增模板'}
        open={editVisible}
        onCancel={() => setEditVisible(false)}
        onOk={handleSubmit}
        confirmLoading={submitLoading}
        okText={editingItem ? '保存' : '创建'}
        width={680}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
          <Form.Item name="title" label="模板标题" rules={[{ required: true, message: '请输入标题' }]}>
            <Input placeholder="请输入模板标题" maxLength={200} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="category" label="分类">
                <Select placeholder="请选择分类" allowClear options={CATEGORY_OPTIONS} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="tags" label="标签" extra="多个标签用逗号分隔">
                <Input placeholder="如：技术方案,IT,软件" maxLength={500} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="content" label="内容">
            <TextArea rows={12} placeholder="请输入模板内容..." />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <TextArea rows={2} placeholder="备注信息" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
