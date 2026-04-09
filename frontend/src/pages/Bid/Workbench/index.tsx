import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Layout, Tree, Button, Select, Input, Space, Tag, Typography,
  Modal, Form, TreeSelect, InputNumber, message, Empty, Spin,
  Tooltip, Dropdown, Card, Drawer, Progress, List,
} from 'antd';
import type { TreeDataNode, MenuProps } from 'antd';
import {
  PlusOutlined, SaveOutlined, ArrowLeftOutlined,
  MoreOutlined, EditOutlined, DeleteOutlined, PlusCircleOutlined,
  FileSearchOutlined, RobotOutlined, SafetyCertificateOutlined, DownloadOutlined,
  CheckCircleFilled, WarningFilled, CloseCircleFilled,
} from '@ant-design/icons';
import {
  getBidProject, getSectionTree, createSection, updateSection, deleteSection,
  aiGenerateSection, bidComplianceCheck, exportBidWord,
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
  const [parseDrawerOpen, setParseDrawerOpen] = useState(false);

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

  // AI 生成状态
  const [aiGenOpen, setAiGenOpen] = useState(false);
  const [aiGenLoading, setAiGenLoading] = useState(false);
  const [aiGenTenderReq, setAiGenTenderReq] = useState('');
  const [aiGenAdditional, setAiGenAdditional] = useState('');
  const [aiGenPreviewOpen, setAiGenPreviewOpen] = useState(false);
  const [aiGenResult, setAiGenResult] = useState('');

  // 废标检查状态
  const [checkDrawerOpen, setCheckDrawerOpen] = useState(false);
  const [checkLoading, setCheckLoading] = useState(false);
  const [checkResult, setCheckResult] = useState<BidCheckResult | null>(null);
  const [checkTenderReq, setCheckTenderReq] = useState('');
  const [checkInputOpen, setCheckInputOpen] = useState(false);

  // 导出状态
  const [exportLoading, setExportLoading] = useState(false);

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

  // AI 生成章节内容
  const handleAiGenerate = async () => {
    if (!selectedSection) return;
    setAiGenOpen(false);
    setAiGenLoading(true);
    const hide = message.loading('AI 正在生成中，请稍候（约 30-60 秒）...', 0);
    try {
      const res = await aiGenerateSection(selectedSection.id, {
        tender_requirements: aiGenTenderReq || undefined,
        additional_context: aiGenAdditional || undefined,
      });
      setAiGenResult(res.data.generated_content);
      setAiGenPreviewOpen(true);
    } catch {
      message.error('AI 生成失败，请重试');
    } finally {
      hide();
      setAiGenLoading(false);
    }
  };

  const handleAiAdopt = () => {
    setEditContent(aiGenResult);
    contentChanged.current = true;
    setAiGenPreviewOpen(false);
    message.success('已采纳 AI 生成内容');
  };

  const handleAiAppend = () => {
    setEditContent((prev) => (prev ? prev + '\n\n' + aiGenResult : aiGenResult));
    contentChanged.current = true;
    setAiGenPreviewOpen(false);
    message.success('已追加 AI 生成内容');
  };

  // 废标检查
  const handleComplianceCheck = async () => {
    setCheckInputOpen(false);
    setCheckDrawerOpen(true);
    setCheckLoading(true);
    setCheckResult(null);
    try {
      const res = await bidComplianceCheck(projectId, {
        tender_requirements: checkTenderReq || undefined,
      });
      setCheckResult(res.data);
    } catch {
      message.error('废标检查失败，请重试');
    } finally {
      setCheckLoading(false);
    }
  };

  // 导出 Word
  const handleExportWord = async () => {
    if (!project) return;
    setExportLoading(true);
    try {
      const response = await exportBidWord(projectId);
      const url = URL.createObjectURL(new Blob([response.data as BlobPart]));
      const a = document.createElement('a');
      a.href = url;
      a.download = project.title + '.docx';
      a.click();
      URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch {
      message.error('导出失败，请重试');
    } finally {
      setExportLoading(false);
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
        <div style={{ flex: 1 }} />
        <Space>
          <Button
            icon={<SafetyCertificateOutlined />}
            onClick={() => setCheckInputOpen(true)}
            style={{ color: '#d97706', borderColor: '#d97706' }}
          >
            废标检查
          </Button>
          <Button
            icon={<DownloadOutlined />}
            loading={exportLoading}
            onClick={handleExportWord}
            style={{ color: '#0d9488', borderColor: '#0d9488' }}
          >
            导出 Word
          </Button>
        </Space>
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
          {/* 招标文件解析按钮 */}
          <div style={{ padding: '8px 12px', borderBottom: '1px solid #e2e8f0' }}>
            <Button
              type="dashed"
              block
              icon={<FileSearchOutlined />}
              onClick={() => setParseDrawerOpen(true)}
              style={{ color: '#0d9488', borderColor: '#0d9488' }}
            >
              招标文件解析
            </Button>
          </div>

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
                    icon={<RobotOutlined />}
                    loading={aiGenLoading}
                    onClick={() => {
                      setAiGenTenderReq('');
                      setAiGenAdditional('');
                      setAiGenOpen(true);
                    }}
                    style={{ color: '#7c3aed', borderColor: '#7c3aed' }}
                  >
                    AI 生成
                  </Button>
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

      {/* 招标文件解析 Drawer */}
      <Drawer
        title="招标文件智能解析"
        placement="right"
        width={720}
        open={parseDrawerOpen}
        onClose={() => setParseDrawerOpen(false)}
      >
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
                    setParseDrawerOpen(false);
                  } catch {
                    message.error('章节生成失败');
                  }
                },
              });
            }
          }}
        />
      </Drawer>

      {/* AI 生成 - 输入 Modal */}
      <Modal
        title={
          <Space>
            <RobotOutlined style={{ color: '#7c3aed' }} />
            AI 生成章节内容
          </Space>
        }
        open={aiGenOpen}
        onOk={handleAiGenerate}
        onCancel={() => setAiGenOpen(false)}
        okText="开始生成"
        okButtonProps={{ style: { background: 'linear-gradient(135deg, #7c3aed, #8b5cf6)', border: 'none' } }}
        width={520}
        destroyOnClose
      >
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 8, fontWeight: 500, color: '#374151' }}>招标要求（可选）</div>
          <TextArea
            value={aiGenTenderReq}
            onChange={(e) => setAiGenTenderReq(e.target.value)}
            rows={4}
            placeholder="请输入该章节对应的招标要求，如：技术方案需包含系统架构图、实施计划..."
          />
        </div>
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 8, fontWeight: 500, color: '#374151' }}>额外要求（可选）</div>
          <TextArea
            value={aiGenAdditional}
            onChange={(e) => setAiGenAdditional(e.target.value)}
            rows={3}
            placeholder="其他补充要求，如：强调公司在行业内的经验、突出技术优势..."
          />
        </div>
        <div style={{
          padding: '10px 14px',
          background: '#f5f3ff',
          borderRadius: 6,
          fontSize: 12,
          color: '#6d28d9',
        }}>
          AI 将根据招标要求和企业资料库生成初稿内容，生成完成后可选择采纳或追加到当前内容。
        </div>
      </Modal>

      {/* AI 生成 - 预览 Modal */}
      <Modal
        title={
          <Space>
            <RobotOutlined style={{ color: '#7c3aed' }} />
            AI 生成结果预览
          </Space>
        }
        open={aiGenPreviewOpen}
        onCancel={() => setAiGenPreviewOpen(false)}
        footer={
          <Space>
            <Button onClick={() => setAiGenPreviewOpen(false)}>取消</Button>
            <Button onClick={handleAiAppend} style={{ color: '#0d9488', borderColor: '#0d9488' }}>追加到末尾</Button>
            <Button
              type="primary"
              onClick={handleAiAdopt}
              style={{ background: 'linear-gradient(135deg, #7c3aed, #8b5cf6)', border: 'none' }}
            >
              采纳（替换当前内容）
            </Button>
          </Space>
        }
        width={720}
        destroyOnClose
      >
        <TextArea
          value={aiGenResult}
          rows={18}
          readOnly
          style={{ fontSize: 14, lineHeight: 1.8, fontFamily: 'inherit', background: '#fafafa' }}
        />
      </Modal>

      {/* 废标检查 - 输入 Modal */}
      <Modal
        title={
          <Space>
            <SafetyCertificateOutlined style={{ color: '#d97706' }} />
            废标检查
          </Space>
        }
        open={checkInputOpen}
        onOk={handleComplianceCheck}
        onCancel={() => setCheckInputOpen(false)}
        okText="开始检查"
        okButtonProps={{ style: { background: 'linear-gradient(135deg, #d97706, #f59e0b)', border: 'none' } }}
        width={480}
        destroyOnClose
      >
        <div style={{ marginBottom: 8, fontWeight: 500, color: '#374151' }}>招标要求（可选）</div>
        <TextArea
          value={checkTenderReq}
          onChange={(e) => setCheckTenderReq(e.target.value)}
          rows={5}
          placeholder="粘贴招标文件中的关键要求，AI 将逐项核查标书是否满足..."
        />
        <div style={{ marginTop: 12, fontSize: 12, color: '#6b7280' }}>
          不填写则仅做基础格式检查，填写后可按要求逐项核查。
        </div>
      </Modal>

      {/* 废标检查结果 Drawer */}
      <Drawer
        title={
          <Space>
            <SafetyCertificateOutlined style={{ color: '#d97706' }} />
            废标检查报告
          </Space>
        }
        placement="right"
        width={640}
        open={checkDrawerOpen}
        onClose={() => setCheckDrawerOpen(false)}
      >
        {checkLoading ? (
          <div style={{ textAlign: 'center', padding: 80 }}>
            <Spin size="large" tip="正在检查中，请稍候..." />
          </div>
        ) : checkResult ? (
          <div>
            {/* 顶部总分 */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 32,
              padding: '24px 0',
              borderBottom: '1px solid #e2e8f0',
              marginBottom: 24,
              justifyContent: 'center',
            }}>
              <Progress
                type="circle"
                percent={checkResult.score}
                size={100}
                strokeColor={checkResult.score >= 80 ? '#22c55e' : checkResult.score >= 60 ? '#f59e0b' : '#ef4444'}
                format={(pct) => <span style={{ fontSize: 22, fontWeight: 700 }}>{pct}</span>}
              />
              <div>
                <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#0f172a' }}>综合评分</div>
                <Tag
                  color={checkResult.pass ? 'success' : 'error'}
                  style={{ fontSize: 14, padding: '4px 12px' }}
                >
                  {checkResult.pass ? '通过' : '未通过'}
                </Tag>
                {checkResult.missing_sections && checkResult.missing_sections.length > 0 && (
                  <div style={{ marginTop: 8, fontSize: 12, color: '#ef4444' }}>
                    缺失章节：{checkResult.missing_sections.join('、')}
                  </div>
                )}
              </div>
            </div>

            {/* 检查项列表 */}
            <List
              dataSource={checkResult.items}
              renderItem={(item) => {
                const statusIcon =
                  item.status === 'PASS' ? <CheckCircleFilled style={{ color: '#22c55e', fontSize: 16 }} /> :
                  item.status === 'WARN' ? <WarningFilled style={{ color: '#f59e0b', fontSize: 16 }} /> :
                  <CloseCircleFilled style={{ color: '#ef4444', fontSize: 16 }} />;
                return (
                  <List.Item style={{ alignItems: 'flex-start', padding: '12px 0' }}>
                    <div style={{ display: 'flex', gap: 10, width: '100%' }}>
                      <div style={{ marginTop: 2, flexShrink: 0 }}>{statusIcon}</div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, color: '#0f172a', marginBottom: 4 }}>{item.requirement}</div>
                        <div style={{ fontSize: 13, color: '#475569', marginBottom: item.suggestion ? 6 : 0 }}>{item.detail}</div>
                        {item.suggestion && (
                          <div style={{
                            fontSize: 12,
                            color: '#6d28d9',
                            background: '#f5f3ff',
                            padding: '6px 10px',
                            borderRadius: 4,
                            borderLeft: '3px solid #8b5cf6',
                          }}>
                            建议：{item.suggestion}
                          </div>
                        )}
                      </div>
                    </div>
                  </List.Item>
                );
              }}
            />

            {/* 风险警告 */}
            {checkResult.risk_warnings && checkResult.risk_warnings.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontWeight: 600, color: '#dc2626', marginBottom: 8 }}>风险警告</div>
                {checkResult.risk_warnings.map((w, i) => (
                  <div key={i} style={{
                    padding: '8px 12px',
                    background: '#fef2f2',
                    borderRadius: 4,
                    borderLeft: '3px solid #ef4444',
                    marginBottom: 6,
                    fontSize: 13,
                    color: '#7f1d1d',
                  }}>
                    {w}
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <Empty description="暂无检查结果" />
        )}
      </Drawer>
    </div>
  );
}
