import { useEffect, useState } from 'react';
import { Tag, Button, Modal, Checkbox, Spin, Empty, App } from 'antd';
import { LinkOutlined, EditOutlined } from '@ant-design/icons';
import {
  getProjectScoringItems,
  getSectionScoringItems,
  replaceSectionScoringItems,
  type ScoringItem,
} from '@/services/bid';

interface Props {
  projectId: number;
  sectionId: number;
  /** 数据更新时通知父组件刷新（如更新章节列表的"关联 X 项"标签）*/
  onChanged?: () => void;
}

export default function SectionScoringLink({ projectId, sectionId, onChanged }: Props) {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [linked, setLinked] = useState<ScoringItem[]>([]);
  const [allItems, setAllItems] = useState<ScoringItem[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getSectionScoringItems(sectionId);
      setLinked(res.data || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, [sectionId]);

  const openModal = async () => {
    const res = await getProjectScoringItems(projectId);
    setAllItems(res.data || []);
    setSelectedIds(linked.map((it) => it.id));
    setModalOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await replaceSectionScoringItems(sectionId, selectedIds);
      message.success('关联已更新');
      setModalOpen(false);
      await load();
      onChanged?.();
    } catch (err: any) {
      message.error(`保存失败：${err?.message || err}`);
    } finally {
      setSaving(false);
    }
  };

  const totalScore = linked.reduce((sum, it) => sum + (it.max_score || 0), 0);

  return (
    <>
      <div
        style={{
          background: '#f0fdfa',
          border: '1px solid #99f6e4',
          borderRadius: 8,
          padding: '10px 14px',
          marginBottom: 12,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: linked.length > 0 ? 8 : 0 }}>
          <LinkOutlined style={{ color: '#0d9488' }} />
          <span style={{ fontWeight: 500, color: '#0f172a' }}>关联评分项</span>
          {linked.length > 0 ? (
            <Tag color="cyan" style={{ fontSize: 12 }}>{linked.length} 项 / {totalScore} 分</Tag>
          ) : (
            <Tag color="default" style={{ fontSize: 12 }}>未关联</Tag>
          )}
          <div style={{ flex: 1 }} />
          <Button size="small" icon={<EditOutlined />} onClick={openModal}>编辑关联</Button>
        </div>
        {loading ? <Spin size="small" /> : linked.length > 0 && (
          <div>
            {linked.map((it) => (
              <Tag
                key={it.id}
                color="cyan"
                style={{ fontSize: 12, marginBottom: 4 }}
                title={it.criteria}
              >
                {it.item_name} {it.max_score !== null && <span style={{ opacity: 0.7 }}>({it.max_score}分)</span>}
              </Tag>
            ))}
          </div>
        )}
      </div>

      <Modal
        title="关联评分项（多选）"
        open={modalOpen}
        onOk={handleSave}
        confirmLoading={saving}
        onCancel={() => setModalOpen(false)}
        width={720}
        okText="保存"
        cancelText="取消"
      >
        <div style={{ color: '#64748b', fontSize: 13, marginBottom: 12 }}>
          勾选本章节应该响应的评分项。AI 生成时会把所选评分项的细则塞进 prompt，让生成内容更有针对性。
        </div>
        {!allItems.length ? (
          <Empty description="项目暂无评分项" />
        ) : (
          <Checkbox.Group
            value={selectedIds}
            onChange={(v) => setSelectedIds(v as number[])}
            style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 480, overflow: 'auto' }}
          >
            {allItems.map((it) => (
              <Checkbox key={it.id} value={it.id} style={{ alignItems: 'flex-start' }}>
                <div style={{ marginLeft: 4 }}>
                  <span style={{ fontWeight: 500 }}>{it.item_name}</span>
                  {it.max_score !== null && (
                    <Tag color="cyan" style={{ fontSize: 11, marginLeft: 8 }}>
                      {it.max_score}分
                    </Tag>
                  )}
                  <Tag style={{ fontSize: 11 }}>{it.category}</Tag>
                  <div style={{ fontSize: 12, color: '#64748b', marginTop: 4, whiteSpace: 'pre-wrap' }}>
                    {it.criteria}
                  </div>
                </div>
              </Checkbox>
            ))}
          </Checkbox.Group>
        )}
      </Modal>
    </>
  );
}
