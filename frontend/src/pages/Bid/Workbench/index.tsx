import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Layout, Tree, Button, Select, Input, Space, Tag, Typography,
  Modal, Form, TreeSelect, InputNumber, Empty, Spin,
  Tooltip, Dropdown, Card, Drawer, Progress, List, Alert, App, Tabs, Segmented } from 'antd';
import type { TreeDataNode, TreeProps, MenuProps } from 'antd';
import {
  PlusOutlined, SaveOutlined, ArrowLeftOutlined,
  MoreOutlined, EditOutlined, DeleteOutlined, PlusCircleOutlined,
  FileSearchOutlined, RobotOutlined, SafetyCertificateOutlined, DownloadOutlined, StarOutlined,
  CheckCircleFilled, WarningFilled, CloseCircleFilled,
  ThunderboltOutlined, EyeOutlined, DatabaseOutlined,
} from '@ant-design/icons';
import {
  getBidProject, getSectionTree, createSection, updateSection, deleteSection, reorderSections,
  aiGenerateSectionStream, exportBidWord, generateBidFramework,
  previewBidDocument, fillLibrarySections,
  runBidDetection, getDetectReports, getDetectReportDetail,
} from '@/services/bid';
import type { DetectItem, DetectReport, DetectReportListItem } from '@/services/bid';
import { getUserList } from '@/services/system';
import TenderDocParser from '@/components/TenderDocParser';
import MarkdownContent from '@/components/MarkdownContent';
import RichTextEditor from '@/components/RichTextEditor';
import ScoringTablePanel from '@/components/ScoringTablePanel';
import SectionScoringLink from '@/components/SectionScoringLink';
import { LIBRARY_API } from '@/constants/api';

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

// ── 章节类型配置 ──────────────────────────────────────────────
const SECTION_TYPE_CONFIG: Record<string, { color: string; label: string; alertType: 'info' | 'warning' | 'success' | 'error'; alertMsg: string }> = {
  TEMPLATE:    { color: '#3b82f6', label: '模板', alertType: 'info',    alertMsg: '此章节为格式模板，内容已从知识库自动填充，请核对后修改公司信息和项目信息。' },
  MANUAL:      { color: '#f97316', label: '手动', alertType: 'warning', alertMsg: '此章节需要手动填写（如报价信息），请根据招标要求填写。' },
  LIBRARY:     { color: '#22c55e', label: '资料', alertType: 'success', alertMsg: '此章节内容来自企业资料库，请在企业资料库中维护相关资质/业绩/人员/设备信息。' },
  AI_GENERATE: { color: '#7c3aed', label: 'AI',   alertType: 'info',    alertMsg: '此章节可使用 AI 生成内容，点击下方「AI 生成」按钮。' },
  ATTACHMENT:  { color: '#94a3b8', label: '附件', alertType: 'info',    alertMsg: '此章节为附件区，请上传相关扫描件。' },
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

// ── 工具函数：拖拽后重排 sections 树 ───────────────────────────
function applyDrop(
  sections: BidSection[],
  dragKey: number,
  dropKey: number,
  dropPosition: number,        // -1: 拖到 dropKey 之前；1: 之后；0: 内部
  dropToGap: boolean,          // 是否拖到节点之间的间隙
): BidSection[] {
  const data = JSON.parse(JSON.stringify(sections)) as BidSection[];

  // 1. 找到并移除 drag 节点
  let dragNode: BidSection | null = null;
  const remove = (list: BidSection[]): boolean => {
    for (let i = 0; i < list.length; i++) {
      if (list[i].id === dragKey) {
        dragNode = list[i];
        list.splice(i, 1);
        return true;
      }
      if (list[i].children?.length && remove(list[i].children!)) return true;
    }
    return false;
  };
  remove(data);
  if (!dragNode) return sections;

  // 2. 插入到目标位置
  const insert = (list: BidSection[]): boolean => {
    for (let i = 0; i < list.length; i++) {
      if (list[i].id === dropKey) {
        if (!dropToGap) {
          // 拖到节点内部，作为第一个子节点
          list[i].children = list[i].children || [];
          list[i].children!.unshift(dragNode!);
        } else if (dropPosition === -1) {
          list.splice(i, 0, dragNode!);
        } else {
          list.splice(i + 1, 0, dragNode!);
        }
        return true;
      }
      if (list[i].children?.length && insert(list[i].children!)) return true;
    }
    return false;
  };
  insert(data);
  return data;
}

// ── 工具函数：树转 reorder 提交项 ──────────────────────────────
function treeToReorderItems(
  sections: BidSection[],
): { id: number; parent_id: number | null; sort_order: number }[] {
  const items: { id: number; parent_id: number | null; sort_order: number }[] = [];
  const walk = (list: BidSection[], parentId: number | null) => {
    list.forEach((s, idx) => {
      items.push({ id: s.id, parent_id: parentId, sort_order: idx });
      if (s.children?.length) walk(s.children, s.id);
    });
  };
  walk(sections, null);
  return items;
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
  const { message } = App.useApp();
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
      destroyOnHidden
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
      destroyOnHidden
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
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const projectId = Number(id);

  const [project, setProject] = useState<BidProject | null>(null);
  const [sections, setSections] = useState<BidSection[]>([]);
  const [selectedSection, setSelectedSection] = useState<BidSection | null>(null);
  const [loadingProject, setLoadingProject] = useState(true);
  const [loadingTree, setLoadingTree] = useState(false);
  const [parseDrawerOpen, setParseDrawerOpen] = useState(false);
  const [scoringDrawerOpen, setScoringDrawerOpen] = useState(false);

  // 编辑器状态
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');
  const [editStatus, setEditStatus] = useState('PENDING');
  const [editAssigneeId, setEditAssigneeId] = useState<number | undefined>(undefined);
  const [savingContent, setSavingContent] = useState(false);
  const [editorMode, setEditorMode] = useState<'edit' | 'preview'>('edit');

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

  // 标书检测状态
  const [detectDrawerOpen, setDetectDrawerOpen] = useState(false);
  const [detectLoading, setDetectLoading] = useState(false);
  const [detectProgress, setDetectProgress] = useState('');
  const [detectReport, setDetectReport] = useState<DetectReport | null>(null);
  const [detectHistory, setDetectHistory] = useState<DetectReportListItem[]>([]);

  // 导出状态
  const [exportLoading, setExportLoading] = useState(false);

  // 一键生成框架状态
  const [frameworkLoading, setFrameworkLoading] = useState(false);

  // 是否已有解析过的招标文件
  const [hasTenderDoc, setHasTenderDoc] = useState(false);

  // 文档预览状态
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState<{
    project_title: string;
    total_sections: number;
    completed_sections: number;
    total_words: number;
    sections: Array<{
      id: number; title: string; content: string;
      section_type: string; status: string; word_count: number;
    }>;
  } | null>(null);

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

  // 加载是否已有解析过的招标文件
  const loadHasTenderDoc = useCallback(async () => {
    if (!projectId) return;
    try {
      const { getTenderDocsByProject } = await import('@/services/tender_doc');
      const res = await getTenderDocsByProject(projectId);
      const docs = res.data || [];
      setHasTenderDoc(docs.some((d: TenderDocumentInfo) => d.parse_status === 'COMPLETED'));
    } catch {
      setHasTenderDoc(false);
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
    loadHasTenderDoc();
  }, [loadProject, loadSections, loadHasTenderDoc]);

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

  // 章节树拖拽
  const handleTreeDrop: TreeProps['onDrop'] = async (info) => {
    const dragKey = Number(info.dragNode.key);
    const dropKey = Number(info.node.key);
    const dropPos = info.node.pos.split('-');
    const dropPosition = info.dropPosition - Number(dropPos[dropPos.length - 1]);
    // dropToGap = false 表示拖到节点上（成为子节点），true 表示拖到节点之间

    const newSections = applyDrop(sections, dragKey, dropKey, dropPosition, info.dropToGap);
    setSections(newSections);  // 乐观更新
    try {
      await reorderSections(projectId, treeToReorderItems(newSections));
    } catch (err: any) {
      message.error('章节移动失败');
      await loadSections();
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

  // AI 流式生成章节内容
  const handleAiGenerate = async () => {
    if (!selectedSection) return;
    setAiGenOpen(false);
    setAiGenLoading(true);
    setAiGenResult('');
    setAiGenPreviewOpen(true);  // 立即打开预览，实时显示

    await aiGenerateSectionStream(
      selectedSection.id,
      {
        tender_requirements: aiGenTenderReq || undefined,
        additional_context: aiGenAdditional || undefined,
      },
      (chunk) => {
        setAiGenResult((prev) => prev + chunk);
      },
      () => {
        setAiGenLoading(false);
      },
      (err) => {
        message.error(`AI 生成失败: ${err}`);
        setAiGenLoading(false);
      },
    );
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

  // 标书检测
  const handleDetect = async () => {
    setDetectDrawerOpen(true);
    setDetectLoading(true);
    setDetectProgress('正在进行规则预检...');

    const ruleItems: DetectItem[] = [];
    const aiItems: DetectItem[] = [];
    let ruleScore = 100;
    let aiScore = 0;

    await runBidDetection(
      projectId,
      (item) => { ruleItems.push(item); },
      (score, count) => {
        ruleScore = score;
        setDetectProgress(`规则预检完成（${count}项），开始 AI 检测...`);
      },
      (category, current, total) => {
        setDetectProgress(`AI 检测中：${category}（${current}/${total}）`);
      },
      (item) => { aiItems.push(item); },
      (_category, score) => { aiScore += score; },
      (reportId, totalScore, status, summary) => {
        setDetectReport({
          id: reportId,
          project_id: projectId,
          total_score: totalScore,
          status,
          rule_score: ruleScore,
          ai_score: aiScore,
          rule_items: ruleItems,
          ai_items: aiItems,
          summary,
          created_at: new Date().toISOString(),
          created_by: null,
        });
        setDetectLoading(false);
        getDetectReports(projectId).then(res => setDetectHistory(res.data || []));
      },
      (err) => {
        message.error(`检测失败: ${err}`);
        setDetectLoading(false);
      },
    );
  };

  const handleLoadHistoryReport = async (reportId: number) => {
    try {
      const res = await getDetectReportDetail(projectId, reportId);
      setDetectReport(res.data);
    } catch {
      message.error('加载报告失败');
    }
  };

  // 导出 Word
  // 填充资料库章节
  const [fillLibraryLoading, setFillLibraryLoading] = useState(false);
  const handleFillLibrary = async () => {
    setFillLibraryLoading(true);
    try {
      const res = await fillLibrarySections(projectId);
      const filled = res.data || [];
      if (filled.length > 0) {
        message.success(`已填充 ${filled.length} 个资料库章节：${filled.map(s => s.title).join('、')}`);
        await loadSections();
      } else {
        message.info('资料库暂无数据可填充，请先在企业资料库中维护数据');
      }
    } catch {
      message.error('填充失败，请重试');
    } finally {
      setFillLibraryLoading(false);
    }
  };

  // 文档预览
  const handlePreview = async () => {
    setPreviewOpen(true);
    setPreviewLoading(true);
    try {
      const res = await previewBidDocument(projectId);
      setPreviewData(res.data);
    } catch {
      message.error('加载预览失败');
    } finally {
      setPreviewLoading(false);
    }
  };

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

  // 一键生成框架
  const handleGenerateFramework = async () => {
    setFrameworkLoading(true);
    try {
      await generateBidFramework(projectId);
      message.success('框架生成成功，已自动填充章节目录');
      await loadSections();
    } catch {
      message.error('框架生成失败，请重试');
    } finally {
      setFrameworkLoading(false);
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
          {section.section_type && SECTION_TYPE_CONFIG[section.section_type] && (
            <Tag
              style={{
                fontSize: 11,
                padding: '0 4px',
                lineHeight: '16px',
                marginRight: 0,
                color: SECTION_TYPE_CONFIG[section.section_type].color,
                borderColor: SECTION_TYPE_CONFIG[section.section_type].color,
                background: 'transparent',
                flexShrink: 0,
              }}
            >
              {SECTION_TYPE_CONFIG[section.section_type].label}
            </Tag>
          )}
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

  const renderDetectItems = (items: DetectItem[]) => {
    if (!items.length) return <Empty description="此类别暂无检查项" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
    return (
      <List
        size="small"
        dataSource={items}
        renderItem={(item) => {
          const icon = item.status === 'PASS'
            ? <CheckCircleFilled style={{ color: '#22c55e', fontSize: 16 }} />
            : item.status === 'WARNING'
            ? <WarningFilled style={{ color: '#f59e0b', fontSize: 16 }} />
            : <CloseCircleFilled style={{ color: '#ef4444', fontSize: 16 }} />;
          return (
            <List.Item style={{ alignItems: 'flex-start', padding: '10px 0' }}>
              <div style={{ display: 'flex', gap: 10, width: '100%' }}>
                <div style={{ marginTop: 2, flexShrink: 0 }}>{icon}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, color: '#0f172a', marginBottom: 2, fontSize: 13 }}>{item.check_name}</div>
                  {item.source && (
                    <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 2 }}>依据：{item.source}</div>
                  )}
                  <div style={{ fontSize: 13, color: '#475569', marginBottom: item.suggestion ? 4 : 0 }}>{item.detail}</div>
                  {item.suggestion && (
                    <div style={{
                      fontSize: 12, color: '#6d28d9', background: '#f5f3ff',
                      padding: '4px 8px', borderRadius: 4, borderLeft: '3px solid #8b5cf6', marginTop: 4,
                    }}>
                      建议：{item.suggestion}
                    </div>
                  )}
                  {item.section_title && (
                    <Text type="secondary" style={{ fontSize: 11 }}>章节：{item.section_title}</Text>
                  )}
                </div>
              </div>
            </List.Item>
          );
        }}
      />
    );
  };

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
            icon={<DatabaseOutlined />}
            loading={fillLibraryLoading}
            onClick={handleFillLibrary}
            style={{ color: '#22c55e', borderColor: '#22c55e' }}
          >
            填充资料库
          </Button>
          <Button
            icon={<EyeOutlined />}
            onClick={handlePreview}
            style={{ color: '#3b82f6', borderColor: '#3b82f6' }}
          >
            文档预览
          </Button>
          <Button
            icon={<StarOutlined />}
            onClick={() => setScoringDrawerOpen(true)}
            style={{ color: '#0d9488', borderColor: '#0d9488' }}
          >
            评分表
          </Button>
          <Button
            icon={<SafetyCertificateOutlined />}
            loading={detectLoading}
            onClick={handleDetect}
            style={{ color: '#d97706', borderColor: '#d97706' }}
          >
            标书检测
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
          <div style={{ padding: '8px 12px', borderBottom: sections.length === 0 ? 'none' : '1px solid #e2e8f0' }}>
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
          {/* 一键生成框架按钮（仅在没有解析过招标文件、且章节数为 0 时显示） */}
          {sections.length === 0 && !hasTenderDoc && (
            <div style={{ padding: '4px 12px 8px', borderBottom: '1px solid #e2e8f0' }}>
              <Button
                type="dashed"
                block
                icon={<ThunderboltOutlined />}
                loading={frameworkLoading}
                onClick={handleGenerateFramework}
                style={{ color: '#0d9488', borderColor: '#0d9488' }}
              >
                一键生成框架（标准模板）
              </Button>
            </div>
          )}

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
              draggable={{ icon: false }}
              onDrop={handleTreeDrop}
              titleRender={renderTreeTitle}
              style={{ background: 'transparent' }}
              className="bid-tree"
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
              {/* 关联评分项面板（链路 B v1）*/}
              {project?.id && selectedSection.id && (
                <SectionScoringLink
                  projectId={project.id}
                  sectionId={selectedSection.id}
                />
              )}
              {/* 章节类型提示 */}
              {selectedSection.section_type && SECTION_TYPE_CONFIG[selectedSection.section_type] && (
                <Alert
                  type={SECTION_TYPE_CONFIG[selectedSection.section_type].alertType}
                  showIcon
                  closable
                  message={SECTION_TYPE_CONFIG[selectedSection.section_type].alertMsg}
                  style={{
                    borderColor: selectedSection.section_type === 'AI_GENERATE' ? '#c4b5fd' :
                                 selectedSection.section_type === 'ATTACHMENT' ? '#cbd5e1' : undefined,
                    background: selectedSection.section_type === 'AI_GENERATE' ? '#f5f3ff' :
                                selectedSection.section_type === 'ATTACHMENT' ? '#f8fafc' : undefined,
                    color: selectedSection.section_type === 'AI_GENERATE' ? '#6d28d9' :
                           selectedSection.section_type === 'ATTACHMENT' ? '#64748b' : undefined,
                  }}
                />
              )}
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
                {/* LIBRARY类型：附件预览区 */}
                {selectedSection.section_type === 'LIBRARY' && editContent && /\[附件:/.test(editContent) && (
                  <div style={{
                    marginBottom: 12,
                    padding: '12px 16px',
                    background: '#f0fdfa',
                    border: '1px solid #ccfbf1',
                    borderRadius: 8,
                  }}>
                    <Text strong style={{ fontSize: 12, color: '#0d9488', display: 'block', marginBottom: 8 }}>附件列表</Text>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {(editContent.match(/\[附件:[^\]]+\]/g) || []).map((tag, idx) => {
                        const m = tag.match(/\[附件:([^:]+):([^\]]+)\]/);
                        if (!m) return null;
                        const [, fp, fn] = m;
                        const url = LIBRARY_API.FILE_URL(fp);
                        const ext = fp.split('.').pop()?.toLowerCase();
                        const isImage = ['jpg', 'jpeg', 'png'].includes(ext || '');
                        return (
                          <a
                            key={idx}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: 4,
                              padding: '4px 12px',
                              background: '#fff',
                              border: '1px solid #99f6e4',
                              borderRadius: 6,
                              color: '#0d9488',
                              fontSize: 13,
                              textDecoration: 'none',
                            }}
                          >
                            {isImage ? '🖼' : '📄'} {fn}
                          </a>
                        );
                      })}
                    </div>
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
                  <Segmented
                    size="small"
                    value={editorMode}
                    onChange={(v) => setEditorMode(v as 'edit' | 'preview')}
                    options={[
                      { label: '编辑', value: 'edit' },
                      { label: '预览', value: 'preview' },
                    ]}
                  />
                </div>
                {editorMode === 'edit' ? (
                  <RichTextEditor
                    value={editContent}
                    onChange={(md) => { setEditContent(md); contentChanged.current = true; }}
                    placeholder="在此输入章节内容（工具栏支持表格、列表、加粗等）..."
                    minHeight={480}
                  />
                ) : (
                  <div
                    style={{
                      minHeight: 480,
                      padding: '12px 16px',
                      background: '#fff',
                      border: '1px solid #d9d9d9',
                      borderRadius: 6,
                      fontSize: 14,
                    }}
                  >
                    {editContent ? (
                      <MarkdownContent content={editContent} />
                    ) : (
                      <span style={{ color: '#94a3b8' }}>暂无内容</span>
                    )}
                  </div>
                )}
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
          onFrameworkGenerated={async () => {
            const treeRes = await getSectionTree(projectId);
            setSections(treeRes.data);
            await loadHasTenderDoc();
            setParseDrawerOpen(false);
            // 默认选中第 1 章
            const flat = flattenSections(treeRes.data);
            if (flat.length > 0) setSelectedSection(flat[0]);
          }}
        />
      </Drawer>

      {/* 评分表 Drawer（链路 B v1）*/}
      <Drawer
        title={<Space><StarOutlined style={{ color: '#0d9488' }} />招标评分表</Space>}
        placement="right"
        width={760}
        open={scoringDrawerOpen}
        onClose={() => setScoringDrawerOpen(false)}
      >
        {project?.id && (
          <ScoringTablePanel
            projectId={project.id}
            sections={flattenSections(sections).map((s) => ({ id: s.id, title: s.title }))}
          />
        )}
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
        destroyOnHidden
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

      {/* AI 生成 - 流式预览 Modal */}
      <Modal
        title={
          <Space>
            <RobotOutlined style={{ color: '#7c3aed' }} />
            {aiGenLoading ? 'AI 正在生成中...' : 'AI 生成结果预览'}
          </Space>
        }
        open={aiGenPreviewOpen}
        onCancel={() => { if (!aiGenLoading) setAiGenPreviewOpen(false); }}
        closable={!aiGenLoading}
        maskClosable={!aiGenLoading}
        footer={aiGenLoading ? (
          <div style={{ textAlign: 'center', color: '#94a3b8' }}>
            <Spin size="small" style={{ marginRight: 8 }} />
            AI 正在撰写中，请稍候...
          </div>
        ) : (
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
        )}
        width={720}
      >
        <div
          style={{
            fontSize: 14,
            padding: '12px 16px',
            background: '#fafafa',
            borderRadius: 8,
            border: '1px solid #e2e8f0',
            minHeight: 300,
            maxHeight: 500,
            overflow: 'auto',
          }}
        >
          {aiGenResult ? (
            <MarkdownContent content={aiGenResult} />
          ) : (
            <span style={{ color: '#94a3b8' }}>{aiGenLoading ? '等待 AI 响应...' : '暂无内容'}</span>
          )}
          {aiGenLoading && <span style={{ animation: 'blink 1s infinite', borderRight: '2px solid #0d9488' }}>&nbsp;</span>}
        </div>
      </Modal>

      {/* 标书检测 Drawer */}
      <Drawer
        title={<Space><SafetyCertificateOutlined style={{ color: '#d97706' }} />标书检测报告</Space>}
        placement="right"
        width={720}
        open={detectDrawerOpen}
        onClose={() => setDetectDrawerOpen(false)}
      >
        {detectLoading ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16, color: '#64748b', fontSize: 14 }}>{detectProgress}</div>
          </div>
        ) : detectReport ? (
          <div>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 24,
              padding: '20px 0', borderBottom: '1px solid #e2e8f0', marginBottom: 16,
            }}>
              <Progress
                type="circle"
                percent={detectReport.total_score}
                size={90}
                strokeColor={detectReport.total_score >= 80 ? '#22c55e' : detectReport.total_score >= 60 ? '#f59e0b' : '#ef4444'}
                format={(pct) => <span style={{ fontSize: 20, fontWeight: 700 }}>{pct}</span>}
              />
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', gap: 12, marginBottom: 8 }}>
                  <Tag color={detectReport.status === 'PASS' ? 'success' : detectReport.status === 'WARNING' ? 'warning' : 'error'} style={{ fontSize: 14, padding: '2px 12px' }}>
                    {detectReport.status === 'PASS' ? '通过' : detectReport.status === 'WARNING' ? '需关注' : '不合规'}
                  </Tag>
                  <Text type="secondary" style={{ fontSize: 12 }}>规则 {detectReport.rule_score}分 | AI {detectReport.ai_score}分</Text>
                </div>
                <div style={{ fontSize: 13, color: '#475569' }}>{detectReport.summary}</div>
                <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 12 }}>
                  <span style={{ color: '#22c55e' }}>通过 {[...detectReport.rule_items, ...detectReport.ai_items].filter(i => i.status === 'PASS').length}</span>
                  <span style={{ color: '#f59e0b' }}>警告 {[...detectReport.rule_items, ...detectReport.ai_items].filter(i => i.status === 'WARNING').length}</span>
                  <span style={{ color: '#ef4444' }}>失败 {[...detectReport.rule_items, ...detectReport.ai_items].filter(i => i.status === 'FAIL').length}</span>
                </div>
              </div>
            </div>
            <Tabs
              size="small"
              items={[
                {
                  key: 'all', label: '全部',
                  children: renderDetectItems([...detectReport.rule_items, ...detectReport.ai_items]
                    .sort((a, b) => {
                      const order: Record<string, number> = { FAIL: 0, WARNING: 1, PASS: 2 };
                      return (order[a.status] ?? 3) - (order[b.status] ?? 3);
                    })),
                },
                { key: 'rule', label: '规则预检', children: renderDetectItems(detectReport.rule_items) },
                { key: 'qual', label: '资格条件', children: renderDetectItems(detectReport.ai_items.filter(i => i.category === '资格条件')) },
                { key: 'score', label: '评分覆盖', children: renderDetectItems(detectReport.ai_items.filter(i => i.category === '评分覆盖')) },
                { key: 'tech', label: '技术响应', children: renderDetectItems(detectReport.ai_items.filter(i => i.category === '技术响应')) },
                { key: 'biz', label: '商务风险', children: renderDetectItems(detectReport.ai_items.filter(i => i.category === '商务风险')) },
                { key: 'fmt', label: '格式合规', children: renderDetectItems(detectReport.ai_items.filter(i => i.category === '格式合规')) },
              ]}
            />
            {detectHistory.length > 1 && (
              <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #e2e8f0' }}>
                <Text strong style={{ fontSize: 13, color: '#475569' }}>历史检测</Text>
                <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {detectHistory.map(h => (
                    <div
                      key={h.id}
                      onClick={() => handleLoadHistoryReport(h.id)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 8,
                        padding: '6px 10px', borderRadius: 6, cursor: 'pointer',
                        background: h.id === detectReport.id ? '#f0fdfa' : '#f8fafc',
                        border: h.id === detectReport.id ? '1px solid #99f6e4' : '1px solid #e2e8f0',
                      }}
                    >
                      <Tag color={h.status === 'PASS' ? 'success' : h.status === 'WARNING' ? 'warning' : 'error'} style={{ fontSize: 11 }}>
                        {h.total_score}分
                      </Tag>
                      <Text style={{ fontSize: 12, flex: 1 }} ellipsis>{h.summary}</Text>
                      <Text type="secondary" style={{ fontSize: 11 }}>{h.created_at?.slice(0, 16).replace('T', ' ')}</Text>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <Empty description="暂无检测结果" />
        )}
      </Drawer>

      {/* 文档预览 Drawer */}
      <Drawer
        title={
          <Space>
            <EyeOutlined style={{ color: '#3b82f6' }} />
            文档预览
          </Space>
        }
        placement="right"
        width={800}
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        extra={
          previewData ? (
            <Space size="middle">
              <Text type="secondary" style={{ fontSize: 12 }}>
                {previewData.completed_sections}/{previewData.total_sections} 章节已完成
              </Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                共 {previewData.total_words.toLocaleString()} 字
              </Text>
            </Space>
          ) : null
        }
      >
        {previewLoading ? (
          <div style={{ textAlign: 'center', padding: 80 }}>
            <Spin size="large" tip="加载中..." />
          </div>
        ) : previewData ? (
          <div style={{ fontFamily: 'SimSun, serif' }}>
            {/* 标题 */}
            <h1 style={{
              textAlign: 'center',
              fontSize: 22,
              fontWeight: 700,
              color: '#0f172a',
              marginBottom: 32,
              paddingBottom: 16,
              borderBottom: '2px solid #0d9488',
            }}>
              {previewData.project_title}
            </h1>

            {/* 章节内容 */}
            {previewData.sections.map((section, index) => (
              <div key={section.id} style={{ marginBottom: 28 }}>
                {/* 章节标题 */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  marginBottom: 12,
                  cursor: 'pointer',
                }}
                  onClick={() => {
                    // 点击跳转到对应章节编辑
                    const target = sections.find(s => s.id === section.id);
                    if (target) {
                      setSelectedSection(target);
                      setPreviewOpen(false);
                    }
                  }}
                >
                  <h2 style={{
                    fontSize: 16,
                    fontWeight: 600,
                    color: '#0f172a',
                    margin: 0,
                  }}>
                    {index + 1}. {section.title}
                  </h2>
                  <Tag
                    color={SECTION_TYPE_CONFIG[section.section_type]?.color}
                    style={{ fontSize: 11 }}
                  >
                    {SECTION_TYPE_CONFIG[section.section_type]?.label}
                  </Tag>
                  {section.status !== 'COMPLETED' && (
                    <Tag color={section.status === 'WRITING' ? 'processing' : 'default'} style={{ fontSize: 11 }}>
                      {section.status === 'PENDING' ? '待处理' : '编写中'}
                    </Tag>
                  )}
                </div>

                {/* 章节内容 */}
                {section.content ? (
                  <div style={{
                    fontSize: 14,
                    color: '#1e293b',
                    paddingLeft: 16,
                    borderLeft: '3px solid #e2e8f0',
                  }}>
                    <MarkdownContent content={section.content} />
                  </div>
                ) : (
                  <div style={{
                    padding: '12px 16px',
                    background: '#fef3c7',
                    borderRadius: 6,
                    color: '#92400e',
                    fontSize: 13,
                  }}>
                    此章节暂无内容
                    {section.section_type === 'AI_GENERATE' && ' — 可使用 AI 生成'}
                    {section.section_type === 'MANUAL' && ' — 需手动填写'}
                    {section.section_type === 'LIBRARY' && ' — 需从企业资料库导入'}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <Empty description="暂无数据" />
        )}
      </Drawer>
    </div>
  );
}
