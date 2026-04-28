import { useEffect, useState } from 'react';
import { Spin, Empty, Tag, Card, Tooltip } from 'antd';
import { getProjectScoringItems, type ScoringItem } from '@/services/bid';

interface Props {
  projectId: number | undefined;
  /** 当前章节树（可选）：用于展示评分项关联了哪些章节 */
  sections?: Array<{ id: number; title: string }>;
}

const CATEGORY_COLORS: Record<string, string> = {
  '技术': '#0d9488',
  '商务': '#7c3aed',
  '价格': '#d97706',
};

export default function ScoringTablePanel({ projectId, sections = [] }: Props) {
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<ScoringItem[]>([]);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    getProjectScoringItems(projectId)
      .then((res) => setItems(res.data || []))
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) return <Spin />;
  if (!items.length) return <Empty description="暂无评分项（招标文件解析中可能未识别到评分细则）" />;

  // 按 category 分组
  const grouped: Record<string, ScoringItem[]> = {};
  items.forEach((it) => {
    const k = it.category || '其他';
    grouped[k] = grouped[k] || [];
    grouped[k].push(it);
  });

  const sectionTitleById = new Map(sections.map((s) => [s.id, s.title]));

  return (
    <div>
      {Object.entries(grouped).map(([cat, list]) => {
        const totalScore = list.reduce((sum, it) => sum + (it.max_score || 0), 0);
        return (
          <div key={cat} style={{ marginBottom: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <Tag color={CATEGORY_COLORS[cat] || '#64748b'} style={{ fontSize: 13, padding: '2px 10px' }}>
                {cat}
              </Tag>
              <span style={{ color: '#0f172a', fontWeight: 600 }}>合计 {totalScore} 分</span>
              <span style={{ color: '#94a3b8', fontSize: 12 }}>（{list.length} 项）</span>
            </div>

            {list.map((it) => {
              const linkedTitles = (it.linked_section_ids || [])
                .map((sid) => sectionTitleById.get(sid))
                .filter(Boolean) as string[];
              return (
                <Card
                  key={it.id}
                  size="small"
                  style={{ marginBottom: 10 }}
                  styles={{ body: { padding: '10px 14px' } }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                    <span style={{ fontWeight: 600, color: '#0f172a', flex: 1 }}>
                      {it.item_name}
                    </span>
                    {it.max_score !== null && (
                      <Tag color="cyan" style={{ fontSize: 12, fontWeight: 600 }}>
                        {it.max_score} 分
                      </Tag>
                    )}
                  </div>
                  <div style={{ marginTop: 6, fontSize: 13, color: '#475569', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                    {it.criteria}
                  </div>
                  {it.required_evidence && (
                    <div style={{ marginTop: 6, fontSize: 12, color: '#64748b' }}>
                      <span style={{ color: '#0d9488', fontWeight: 500 }}>需提供：</span>
                      {it.required_evidence}
                    </div>
                  )}
                  {linkedTitles.length > 0 ? (
                    <div style={{ marginTop: 6 }}>
                      {linkedTitles.map((t) => (
                        <Tag key={t} color="green" style={{ fontSize: 11 }}>
                          关联：{t}
                        </Tag>
                      ))}
                    </div>
                  ) : (
                    <Tooltip title={it.linked_chapter_hint ? `AI 建议关联：${it.linked_chapter_hint}` : '未自动关联到章节'}>
                      <Tag color="default" style={{ fontSize: 11, marginTop: 6 }}>
                        未关联章节
                      </Tag>
                    </Tooltip>
                  )}
                </Card>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
