import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Layout, Tree, Button, Select, Input, Space, Tag, Typography,
  Modal, Form, TreeSelect, InputNumber, message, Empty, Spin,
  Tooltip, Dropdown, Card, Collapse,
} from 'antd';
import type { TreeDataNode, MenuProps } from 'antd';
import {
  PlusOutlined, SaveOutlined, ArrowLeftOutlined,
  MoreOutlined, EditOutlined, DeleteOutlined, PlusCircleOutlined,
  FileSearchOutlined,
} from '@ant-design/icons';
import {
  getBidProject, getSectionTree, createSection, updateSection, deleteSection,
} from '@/services/bid';
import { getUserList } from '@/services/system';
import TenderDocParser from '@/components/TenderDocParser';

const { Sider, Content } = Layout;
const { Text, Title } = Typography;
const { TextArea } = Input;

// ── 状态配置 ──────────────────────────────────────────────────
const SECTION_STATUS_OPTIONS = [
  { value: 'PENDING',   label: '待处理' },
  { value: 'WRITING',   label: '编写中' },
  { value: 'COMPLETED', label: '已完成' },
];

const SECTION_STATUS_DOT: Record<string, string> = {
  PENDING:   '#94a3b8',
  WRITING:   '#3b82f6',
  COMPLETED: '#22c55e',
};

// ── 工具函数：将章节树转为 Ant Tree DataNode ──────────────────
function sectionsToTreeData(sections: BidSection[]): TreeDataNode[] {
  return sections.map((s) => ({
    key: s.id,
    title: s.title,
    children: s.children ? sectionsToTreeData(s.children) : [],
    data: s,
  } as TreeDataNode & { data: BidSection }));
}

// ── 工具函数：将章节树转为 TreeSelect 数据 ─────────────────────
function sectionsToTreeSelectData(sections: BidSection[]): object[] {
  return sections.map((s) => ({
    value: s.id,
    title: s.title,
    children: s.children ? sectionsToTreeSelectData(s.children) : [],
  }));
}

// ── 工具函数：拍平章节树 ──────────────────────────────────────
function flattenSections(sections: BidSection[]): BidSection[] {
  const result: BidSection[] = [];
  const walk = (list: BidSection[]) => {
    for (const s of list) {
      result.push(s);
      if (s.children) walk(s.children);
    }
  };
  walk(sections);
  return result;
}

// ── AddSectionModal 组件 ──────────────────────────────────────
interface AddSectionModalProps {
  open: boolean;
  projectId: number;
  sections: BidSection[];
  defaultParentId?: number;
  onOk: () => void;
  onCancel: () => void;
}

function AddSectionModal({ open, projectId, sections, defaultParentId, onOk, onCancel }: AddSectionModalProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      form.resetFields();
      form.setFieldsValue({
        parent_id: defaultParentId ?? undefined,
        sort_order: 1,
      });
    }
  }, [open, defaultParentId, form]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      await createSection({
        project_id: projectId,
        title: values.title,
        parent_id: values.parent_id ?? undefined,
        sort_order: values.sort_order ?? 1,
      });
      message.success('章节创建成功');
      onOk();
    } catch (e) {
      // validation error or api error
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="新增章节"
      open={open}
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={loading}
      width={480}
      okText="创建"
      destroyOnClose
    >
      <Form form={form} layout="vertical">
        <Form.Item name="title" label="章节标题" rules={[{ required: true, message: '请输入章节标题' }]}>
          <Input placeholder="请输入章节标题" />
        </Form.Item>
        <Form.Item name="parent_id" label="父章节（留空表示根章节）">
          <TreeSelect
            placeholder="请选择父章节（可为空）"
            allowClear
            treeDefaultExpandAll
            treeData={sectionsToTreeSelectData(sections) as Parameters<typeof TreeSelect>[0]['treeData']}
          />
        </Form.Item>
        <Form.Item name="sort_order" label="排序号">
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ── EditTitleModal 组件 ───────────────────────────────────────
interface EditTitleModalProps {
  open: boolean;
  section: BidSection | null;
  onOk: (title: string) => Promise<void>;
  onCancel: () => void;
}

function EditTitleModal({ open, section, onOk, onCancel }: EditTitleModalProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && section) {
      form.setFieldsValue({ title: section.title });
    }
  }, [open, section, form]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      await onOk(values.title);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="编辑章节标题"
      open={open}
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={loading}
      width={400}
      okText="保存"
      destroyOnClose
    >
      <Form form={form} layout="vertical">
        <Form.Item name="title" label="章节标题" rules={[{ required: true, message: '请输入章节标题' }]}>
          <Input placeholder="请输入章节标题" />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ── 主页面 ────────────────────────────────────────────────────
export default function BidWorkbenchPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const projectId = Number(id);

  const [project, setProject] = useState<BidProject | null>(null);
  const [sections, setSections] = useState<BidSection[]>([]);
  const [selectedSection, setSelectedSection] = useState<BidSection | null>(null);
  const [loadingProject, setLoadingProject] = useState(true);
  const [loadingTree, setLoadingTree] = useState(false);

  // 编辑器状态
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');
  const [editStatus, setEditStatus] = useState('PENDING');
  const [editAssigneeId, setEditAssigneeId] = useState<number | undefined>(undefined);
  const [savingContent, setSavingContent] = useState(false);

  // 用户选项
  const [userOptions, setUserOptions] = useState<{ value: number; label: string }[]>([]);

  // 模态框状态
  const [addSectionOpen, setAddSectionOpen] = useState(false);
  const [addSectionParentId, setAddSectionParentId] = useState<number | undefined>(undefined);
  const [editTitleOpen, setEditTitleOpen] = useState(false);
  const [editTitleSection, setEditTitleSection] = useState<BidSection | null>(null);

  const contentChanged = useRef(false);

  // 加载项目信息
  const loadProject = useCallback(async () => {
    if (!projectId) return;
    setLoadingProject(true);
    try {
      const res = await getBidProject(projectId);
      setProject(res.data);
    } finally {
      setLoadingProject(false);
    }
  }, [projectId]);

  // 加载章节树
  const loadSections = useCallback(async () => {
    if (!projectId) return;
    setLoadingTree(true);
    try {
      const res = await getSectionTree(projectId);
      setSections(res.data);
    } finally {
      setLoadingTree(false);
    }
  }, [projectId]);

  // 加载用户列表
  useEffect(() => {
    getUserList({ page: 1, page_size: 100 })
      .then((res) => {
        setUserOptions(res.data.items.map((u: SystemUser) => ({ value: u.id, label: u.real_name })));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadProject();
    loadSections();
  }, [loadProject, loadSections]);

  // 选中章节时同步编辑区
  useEffect(() => {
    if (selectedSection) {
      setEditTitle(selectedSection.title);
      setEditContent(selectedSection.content || '');
      setEditStatus(selectedSection.status);
      setEditAssigneeId(selectedSection.assignee_id);
      contentChanged.current = false;
    }
  }, [selectedSection]);

  // 点击树节点
  const handleSelectNode = useCallback((selectedKeys: React.Key[]) => {
    if (!selectedKeys.length) return;
    const sectionId = Number(selectedKeys[0]);
    const flat = flattenSections(sections);
    const found = flat.find((s) => s.id === sectionId);
    if (found) setSelectedSection(found);
  }, [sections]);

  // 保存章节内容
  const handleSaveContent = async () => {
    if (!selectedSection) return;
    setSavingContent(true);
    try {
      const wordCount = editContent.replace(/\s/g, '').length;
      await updateSection(selectedSection.id, {
        title: editTitle,
        content: editContent,
        status: editStatus,
        assignee_id: editAssigneeId,
        word_count: wordCount,
      });
      message.success('保存成功');
      contentChanged.current = false;
      // 刷新章节树（更新标题/状态显示）
      await loadSections();
      // 更新本地选中
      setSelectedSection((prev) => prev ? { ...prev, title: editTitle, content: editContent, status: editStatus, assignee_id: editAssigneeId, word_count: wordCount } : prev);
    } catch {
      message.error('保存失败');
    } finally {
      setSavingContent(false);
    }
  };

  // 删除章节
  const handleDeleteSection = async (sectionId: number) => {
    try {
      await deleteSection(sectionId);
      message.success('章节已删除');
      if (selectedSection?.id === sectionId) {
        setSelectedSection(null);
      }
      await loadSections();
    } catch {
      message.error('删除失败');
    }
  };

  // 编辑章节标题
  const handleEditTitle = async (title: string) => {
    if (!editTitleSection) return;
    await updateSection(editTitleSection.id, { title });
    message.success('章节标题已更新');
    setEditTitleOpen(false);
    await loadSections();
    if (selectedSection?.id === editTitleSection.id) {
      setSelectedSection((prev) => prev ? { ...prev, title } : prev);
      setEditTitle(title);
    }
  };

  // 渲染树节点标题
  const renderTreeTitle = (node: TreeDataNode & { data?: BidSection }) => {
    const section = node.data;
    if (!section) return <span>{String(node.title)}</span>;

    const dotColor = SECTION_STATUS_DOT[section.status] || '#94a3b8';

    const menuItems: MenuProps['items'] = [
      {
        key: 'add-child',
        icon: <PlusCircleOutlined />,
        label: '新增子章节',
        onClick: () => {
          setAddSectionParentId(section.id);
          setAddSectionOpen(true);
        },
      },
      {
        key: 'edit-title',
        icon: <EditOutlined />,
        label: '编辑标题',
        onClick: () => {
          setEditTitleSection(section);
          setEditTitleOpen(true);
        },
      },
      {
        type: 'divider',
      },
      {
        key: 'delete',
        icon: <DeleteOutlined />,
        label: '删除章节',
        danger: true,
        onClick: () => {
          Modal.confirm({
            title: '确定删除该章节？',
            content: '删除后子章节也将一并删除',
            okType: 'danger',
            onOk: () => handleDeleteSection(section.id),
          });
        },
      },
    ];

    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, paddingRight: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, minWidth: 0 }}>
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: dotColor,
              flexShrink: 0,
              display: 'inline-block',
            }}
          />
          <span style={{ fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {section.title}
          </span>
        </div>
        <Dropdown menu={{ items: menuItems }} trigger={['click']}>
          <Button
            type="text"
            size="small"
            icon={<MoreOutlined />}
            style={{ flexShrink: 0, opacity: 0.5 }}
            onClick={(e) => e.stopPropagation()}
          />
        </Dropdown>
      </div>
    );
  };

  const treeData = sectionsToTreeData(sections).map((node) => ({
    ...node,
    title: renderTreeTitle(node as TreeDataNode & { data?: BidSection }),
  }));

  const wordCount = editContent.replace(/\s/g, '').length;

  if (loadingProject) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!project) {
    return (
      <Card>
        <Empty description="标书项目不存在" />
      </Card>
    );
  }

  return (
    <div style={{ height: 'calc(100vh - 112px)', display: 'flex', flexDirection: 'column' }}>
      {/* 顶部工具栏 */}
      <div style={{
        padding: '12px 20px',
        background: '#fff',
        borderBottom: '1px solid #e2e8f0',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        marginBottom: 0,
        borderRadius: '8px 8px 0 0',
      }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/bid/list')}
          style={{ color: '#64748b' }}
        >
          返回列表
        </Button>
        <div style={{ width: 1, height: 20, background: '#e2e8f0' }} />
        <Title level={5} style={{ margin: 0, color: '#0f172a' }}>{project.title}</Title>
        <Tag color={project.status === 'SUBMITTED' ? 'success' : project.status === 'IN_PROGRESS' ? 'processing' : 'default'}>
          {project.status === 'DRAFT' ? '草稿' : project.status === 'IN_PROGRESS' ? '编制中' : project.status === 'REVIEW' ? '审核中' : '已提交'}
        </Tag>
      </div>

      {/* 左右分栏 */}
      <Layout style={{ flex: 1, overflow: 'hidden', borderRadius: '0 0 8px 8px', background: '#fff' }}>
        {/* 左侧章节树 */}
        <Sider
          width={300}
          style={{
            background: '#f8fafc',
            borderRight: '1px solid #e2e8f0',
            overflow: 'auto',
            padding: '0',
          }}
        >
          {/* 招标文件解析区域 */}
          <Collapse
            ghost
            size="small"
            style={{ borderBottom: '1px solid #e2e8f0', borderRadius: 0 }}
            items={[
              {
                key: 'tender-doc',
                label: (
                  <Space size={6}>
                    <FileSearchOutlined style={{ color: '#0d9488' }} />
                    <Text strong style={{ fontSize: 13, color: '#475569' }}>招标文件解析</Text>
                  </Space>
                ),
                children: (
                  <div style={{ padding: '0 4px 8px' }}>
                    <TenderDocParser
                      projectId={project?.id}
                      tenderId={project?.tender_id}
                      onParseComplete={(result) => {
                        if (result.bid_document_requirements?.chapters && result.bid_document_requirements.chapters.length > 0) {
                          Modal.confirm({
                            title: '自动生成章节',
                            content: `解析到 ${result.bid_document_requirements.chapters.length} 个章节建议：${result.bid_document_requirements.chapters.slice(0, 5).join('、')}${result.bid_document_requirements.chapters.length > 5 ? ' 等' : ''}。是否自动生成章节？`,
                            okText: '自动生成',
                            cancelText: '暂不',
                            onOk: async () => {
                              try {
                                for (let i = 0; i < result.bid_document_requirements!.chapters!.length; i++) {
                                  await createSection({
                                    project_id: projectId,
                                    title: result.bid_document_requirements!.chapters![i],
                                    sort_order: i + 1,
                                  });
                                }
                                message.success(`已生成 ${result.bid_document_requirements!.chapters!.length} 个章节`);
                                await loadSections();
                              } catch {
                                message.error('章节生成失败');
                              }
                            },
                          });
                        }
                      }}
                    />
                  </div>
                ),
              },
            ]}
          />

          <div style={{ padding: '12px 12px 8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Text strong style={{ fontSize: 13, color: '#475569' }}>章节目录</Text>
            <Tooltip title="新增根章节">
              <Button
                type="primary"
                size="small"
                icon={<PlusOutlined />}
                onClick={() => { setAddSectionParentId(undefined); setAddSectionOpen(true); }}
                style={{ background: 'linear-gradient(135deg, #0d9488, #14b8a6)', border: 'none' }}
              />
            </Tooltip>
          </div>

          {loadingTree ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin />
            </div>
          ) : sections.length === 0 ? (
            <div style={{ padding: '20px 16px', textAlign: 'center' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>暂无章节，点击 + 新增</Text>
            </div>
          ) : (
            <Tree
              treeData={treeData}
              defaultExpandAll
              selectedKeys={selectedSection ? [selectedSection.id] : []}
              onSelect={handleSelectNode}
              blockNode
              style={{ background: 'transparent' }}
            />
          )}
        </Sider>

        {/* 右侧内容编辑区 */}
        <Content style={{ padding: 24, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
          {!selectedSection ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <Text type="secondary">
                    请在左侧选择章节开始编辑
                  </Text>
                }
              />
            </div>
          ) : (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* 章节信息栏 */}
              <div style={{
                padding: '16px 20px',
                background: '#f0fdfa',
                borderRadius: 8,
                border: '1px solid #ccfbf1',
                display: 'flex',
                alignItems: 'center',
                gap: 16,
                flexWrap: 'wrap',
              }}>
                {/* 章节标题编辑 */}
                <div style={{ flex: 1, minWidth: 200 }}>
                  <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>章节标题</Text>
                  <Input
                    value={editTitle}
                    onChange={(e) => { setEditTitle(e.target.value); contentChanged.current = true; }}
                    bordered={false}
                    style={{ fontWeight: 600, fontSize: 15, padding: 0, borderBottom: '1px solid #e2e8f0' }}
                  />
                </div>

                {/* 状态 */}
                <div>
                  <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>状态</Text>
                  <Select
                    value={editStatus}
                    onChange={(v) => { setEditStatus(v); contentChanged.current = true; }}
                    options={SECTION_STATUS_OPTIONS}
                    style={{ width: 110 }}
                    size="small"
                  />
                </div>

                {/* 负责人 */}
                <div>
                  <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>负责人</Text>
                  <Select
                    value={editAssigneeId}
                    onChange={(v) => { setEditAssigneeId(v); contentChanged.current = true; }}
                    options={userOptions}
                    allowClear
                    placeholder="选择负责人"
                    style={{ width: 130 }}
                    size="small"
                  />
                </div>

                {/* 字数统计 */}
                <div>
                  <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>字数统计</Text>
                  <Text style={{ fontSize: 13, color: '#0d9488', fontWeight: 600 }}>{wordCount} 字</Text>
                </div>
              </div>

              {/* 内容编辑区 */}
              <div style={{ flex: 1 }}>
                <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>章节内容</Text>
                <TextArea
                  value={editContent}
                  onChange={(e) => { setEditContent(e.target.value); contentChanged.current = true; }}
                  rows={20}
                  placeholder="在此输入章节内容..."
                  style={{
                    fontSize: 14,
                    lineHeight: 1.8,
                    resize: 'vertical',
                    fontFamily: 'inherit',
                  }}
                />
              </div>

              {/* 底部保存按钮 */}
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <Space>
                  <Button
                    type="primary"
                    icon={<SaveOutlined />}
                    loading={savingContent}
                    onClick={handleSaveContent}
                    style={{ background: 'linear-gradient(135deg, #0d9488, #14b8a6)', border: 'none' }}
                  >
                    保存章节
                  </Button>
                </Space>
              </div>
            </div>
          )}
        </Content>
      </Layout>

      {/* 新增章节 Modal */}
      <AddSectionModal
        open={addSectionOpen}
        projectId={projectId}
        sections={sections}
        defaultParentId={addSectionParentId}
        onOk={async () => { setAddSectionOpen(false); await loadSections(); }}
        onCancel={() => setAddSectionOpen(false)}
      />

      {/* 编辑章节标题 Modal */}
      <EditTitleModal
        open={editTitleOpen}
        section={editTitleSection}
        onOk={handleEditTitle}
        onCancel={() => setEditTitleOpen(false)}
      />
    </div>
  );
}
