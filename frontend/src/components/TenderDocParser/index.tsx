import { useState, useEffect } from 'react';
import {
  Upload, Spin, Tabs, Descriptions, Timeline, List, Table, Alert,
  Button, Typography, Tag, Space, App, Progress } from 'antd';
import type { UploadProps } from 'antd';
import {
  InboxOutlined, FileTextOutlined, ClockCircleOutlined,
  SafetyCertificateOutlined, BarChartOutlined, WarningOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import { uploadTenderDocStream, saveToTender, getTenderDocsByProject, getTenderDocsByTender } from '@/services/tender_doc';
import { generateFrameworkFromTender } from '@/services/bid';

const { Dragger } = Upload;
const { Text, Title } = Typography;

interface TenderDocParserProps {
  projectId?: number;
  tenderId?: number;
  /** 章节框架生成完成后回调（生成的章节数和带模板的数量） */
  onFrameworkGenerated?: (totalSections: number, withContent: number) => void;
  /** 兼容：解析完成后回调 */
  onParseComplete?: (result: TenderParseResult) => void;
}

export default function TenderDocParser({ projectId, tenderId, onParseComplete, onFrameworkGenerated }: TenderDocParserProps) {
  const { message } = App.useApp();
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [genProgress, setGenProgress] = useState<{
    phase: 'extract' | 'create' | 'done';
    message: string;
    sectionsCreated: number;
  } | null>(null);
  const [progressText, setProgressText] = useState('');
  const [progressColor, setProgressColor] = useState('#0d9488');
  const [ocrProgress, setOcrProgress] = useState<{ current: number; total: number } | null>(null);
  const [docInfo, setDocInfo] = useState<TenderDocumentInfo | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [parseStatus, setParseStatus] = useState<TenderDocumentInfo['parse_status'] | null>(null);
  const [loadingExisting, setLoadingExisting] = useState(true);

  // 挂载时加载已存在的解析结果（按项目或招标 ID）
  useEffect(() => {
    let cancelled = false;
    const loadExisting = async () => {
      setLoadingExisting(true);
      try {
        let docs: TenderDocumentInfo[] = [];
        if (projectId) {
          const res = await getTenderDocsByProject(projectId);
          docs = res.data || [];
        } else if (tenderId) {
          const res = await getTenderDocsByTender(tenderId);
          docs = res.data || [];
        }
        if (cancelled) return;
        // 取最新一份已解析完成的文档
        const latest = docs.find(d => d.parse_status === 'COMPLETED' && d.parse_result);
        if (latest) {
          setDocInfo(latest);
          setParseStatus(latest.parse_status);
        }
      } catch {
        // 静默失败，让用户重新上传
      } finally {
        if (!cancelled) setLoadingExisting(false);
      }
    };
    loadExisting();
    return () => { cancelled = true; };
  }, [projectId, tenderId]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setProgressText('准备上传...');
    setProgressColor('#0d9488');
    setOcrProgress(null);
    setErrorMsg(null);
    setDocInfo(null);
    try {
      const info = await uploadTenderDocStream(file, projectId, tenderId, (event) => {
        switch (event.type) {
          case 'uploading':
            setProgressText('上传中...');
            setProgressColor('#0d9488');
            break;
          case 'extracting':
            setProgressText('提取文本...');
            setProgressColor('#3b82f6');
            break;
          case 'ocr_start':
            setProgressText(event.message || `开始 OCR（${event.pages_to_process} 页）`);
            setProgressColor('#f59e0b');
            setOcrProgress({ current: 0, total: event.pages_to_process || 0 });
            break;
          case 'ocr_page':
            setProgressText(`OCR 识别中 ${event.current}/${event.total}`);
            setOcrProgress({ current: event.current || 0, total: event.total || 0 });
            break;
          case 'ocr_page_failed':
            setProgressText(`第 ${event.page} 页 OCR 失败，继续...`);
            break;
          case 'ocr_done':
            setProgressText('OCR 完成');
            setOcrProgress(null);
            break;
          case 'parsing':
            setProgressText('AI 智能解析中...');
            setProgressColor('#8b5cf6');
            break;
          case 'linking':
            setProgressText('自动保存到招标信息...');
            setProgressColor('#0d9488');
            break;
          case 'linked':
            setProgressText(event.message || '已关联招标信息');
            break;
          case 'link_failed':
            setProgressText('解析完成（未自动关联招标信息）');
            break;
          case 'done':
            setProgressText('解析完成');
            setProgressColor('#22c55e');
            break;
        }
      });
      setDocInfo(info);
      setParseStatus(info.parse_status);
      if (info.parse_status === 'COMPLETED' && info.parse_result && onParseComplete) {
        onParseComplete(info.parse_result);
      }
      if (info.parse_status === 'FAILED') {
        setErrorMsg(info.error_message || '解析失败，请重试');
      }
    } catch (e: unknown) {
      setParseStatus('FAILED');
      setErrorMsg(e instanceof Error ? e.message : '上传失败，请重试');
    } finally {
      setUploading(false);
    }
    return false;
  };

  const draggerProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.pdf,.docx,.doc',
    beforeUpload: (file) => {
      handleUpload(file);
      return false;
    },
    showUploadList: false,
    disabled: uploading,
  };

  const result = docInfo?.parse_result;

  // Scoring table columns
  const scoringColumns = [
    { title: '分类', dataIndex: 'category', key: 'category', width: 100 },
    { title: '评分项', dataIndex: 'item', key: 'item' },
    { title: '满分', dataIndex: 'max_score', key: 'max_score', width: 70 },
    { title: '评分标准', dataIndex: 'criteria', key: 'criteria' },
  ];

  return (
    <div style={{ padding: '8px 0' }}>
      {/* 加载已存在的解析结果 */}
      {loadingExisting && !docInfo && !uploading && (
        <div style={{ textAlign: 'center', padding: '32px 0' }}>
          <Spin />
          <div style={{ marginTop: 8, fontSize: 12, color: '#94a3b8' }}>加载历史解析结果...</div>
        </div>
      )}

      {/* Upload Area */}
      {!docInfo && !loadingExisting && (
        <Dragger {...draggerProps} style={{ marginBottom: 8 }}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined style={{ color: '#0d9488', fontSize: 32 }} />
          </p>
          <p className="ant-upload-text" style={{ fontSize: 13 }}>
            点击或拖拽招标文件到此处
          </p>
          <p className="ant-upload-hint" style={{ fontSize: 12, color: '#94a3b8' }}>
            支持 PDF、Word (.docx/.doc)，最大 50MB
          </p>
        </Dragger>
      )}

      {/* Upload/Parsing Progress */}
      {uploading && (
        <div style={{ textAlign: 'center', padding: '24px 16px' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, fontSize: 14, fontWeight: 500, color: progressColor }}>
            {progressText}
          </div>
          {ocrProgress && ocrProgress.total > 0 && (
            <div style={{ marginTop: 16, padding: '0 8px' }}>
              <Progress
                percent={Math.round((ocrProgress.current / ocrProgress.total) * 100)}
                strokeColor={progressColor}
                format={() => `${ocrProgress.current} / ${ocrProgress.total}`}
              />
              <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 4 }}>
                每页 OCR 约 30 秒，扫描件总耗时较长，请耐心等待
              </Text>
            </div>
          )}
          {!ocrProgress && (
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 8 }}>
              文本型文件 30~60 秒，扫描件需要逐页 OCR 会更慢
            </Text>
          )}
        </div>
      )}

      {/* Parse Failed */}
      {!uploading && parseStatus === 'FAILED' && (
        <div style={{ marginBottom: 8 }}>
          <Alert
            type="error"
            message="解析失败"
            description={errorMsg || '文件解析失败，请重试'}
            showIcon
          />
          <Button
            type="link"
            size="small"
            style={{ marginTop: 8, padding: 0 }}
            onClick={() => { setDocInfo(null); setParseStatus(null); setErrorMsg(null); }}
          >
            重新上传
          </Button>
        </div>
      )}

      {/* Parse Result */}
      {!uploading && docInfo && parseStatus === 'COMPLETED' && result && (
        <div>
          {/* File Info Header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 12px',
            background: '#f0fdfa',
            borderRadius: 6,
            border: '1px solid #ccfbf1',
            marginBottom: 12,
          }}>
            <FileTextOutlined style={{ color: '#0d9488' }} />
            <Text style={{ flex: 1, fontSize: 13 }}>{docInfo.original_name}</Text>
            <Tag color="success">解析完成</Tag>
            <Button
              type="link"
              size="small"
              style={{ padding: 0, fontSize: 12 }}
              onClick={() => { setDocInfo(null); setParseStatus(null); }}
            >
              重新上传
            </Button>
          </div>

          <Tabs
            size="small"
            items={[
              {
                key: 'basic',
                label: (
                  <Space size={4}>
                    <FileTextOutlined />
                    基本信息
                  </Space>
                ),
                children: result.basic_info ? (
                  <Descriptions column={1} size="small" bordered>
                    {result.basic_info.project_name && (
                      <Descriptions.Item label="项目名称">{result.basic_info.project_name}</Descriptions.Item>
                    )}
                    {result.basic_info.tender_no && (
                      <Descriptions.Item label="招标编号">{result.basic_info.tender_no}</Descriptions.Item>
                    )}
                    {result.basic_info.tender_unit && (
                      <Descriptions.Item label="招标单位">{result.basic_info.tender_unit}</Descriptions.Item>
                    )}
                    {result.basic_info.agent_unit && (
                      <Descriptions.Item label="代理单位">{result.basic_info.agent_unit}</Descriptions.Item>
                    )}
                    {result.basic_info.tender_method && (
                      <Descriptions.Item label="招标方式">{result.basic_info.tender_method}</Descriptions.Item>
                    )}
                    {(result.basic_info.budget_amount_text || result.basic_info.budget_amount !== undefined) && (
                      <Descriptions.Item label="预算金额">
                        {result.basic_info.budget_amount_text || `${result.basic_info.budget_amount} 万元`}
                      </Descriptions.Item>
                    )}
                  </Descriptions>
                ) : (
                  <Text type="secondary" style={{ fontSize: 12 }}>未解析到基本信息</Text>
                ),
              },
              {
                key: 'timeline',
                label: (
                  <Space size={4}>
                    <ClockCircleOutlined />
                    时间节点
                  </Space>
                ),
                children: result.timeline ? (
                  <Timeline
                    items={[
                      result.timeline.publish_date && {
                        color: '#0d9488',
                        children: (
                          <div>
                            <Text strong style={{ fontSize: 13 }}>发布日期</Text>
                            <div><Text type="secondary" style={{ fontSize: 12 }}>{result.timeline.publish_date}</Text></div>
                          </div>
                        ),
                      },
                      result.timeline.question_deadline && {
                        color: '#3b82f6',
                        children: (
                          <div>
                            <Text strong style={{ fontSize: 13 }}>答疑截止</Text>
                            <div><Text type="secondary" style={{ fontSize: 12 }}>{result.timeline.question_deadline}</Text></div>
                          </div>
                        ),
                      },
                      result.timeline.deposit_deadline && {
                        color: '#f59e0b',
                        children: (
                          <div>
                            <Text strong style={{ fontSize: 13 }}>保证金截止</Text>
                            <div>
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                {result.timeline.deposit_deadline}
                                {(result.timeline.deposit_amount_text || result.timeline.deposit_amount !== undefined) && (
                                  <span style={{ marginLeft: 8 }}>
                                    ({result.timeline.deposit_amount_text || `${result.timeline.deposit_amount} 万元`})
                                  </span>
                                )}
                              </Text>
                            </div>
                          </div>
                        ),
                      },
                      result.timeline.bid_deadline && {
                        color: '#ef4444',
                        children: (
                          <div>
                            <Text strong style={{ fontSize: 13 }}>投标截止</Text>
                            <div><Text type="secondary" style={{ fontSize: 12 }}>{result.timeline.bid_deadline}</Text></div>
                          </div>
                        ),
                      },
                      result.timeline.open_bid_time && {
                        color: '#8b5cf6',
                        children: (
                          <div>
                            <Text strong style={{ fontSize: 13 }}>开标时间</Text>
                            <div>
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                {result.timeline.open_bid_time}
                                {result.timeline.open_bid_place && (
                                  <span style={{ marginLeft: 8 }}>@ {result.timeline.open_bid_place}</span>
                                )}
                              </Text>
                            </div>
                          </div>
                        ),
                      },
                    ].filter(Boolean) as { color: string; children: React.ReactNode }[]}
                  />
                ) : (
                  <Text type="secondary" style={{ fontSize: 12 }}>未解析到时间节点</Text>
                ),
              },
              {
                key: 'qualification',
                label: (
                  <Space size={4}>
                    <SafetyCertificateOutlined />
                    资质要求
                  </Space>
                ),
                children: result.qualification ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {result.qualification.required_certs && result.qualification.required_certs.length > 0 && (
                      <div>
                        <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 6 }}>必须资质证书</Text>
                        <List
                          size="small"
                          dataSource={result.qualification.required_certs}
                          renderItem={(cert) => (
                            <List.Item style={{ padding: '4px 0' }}>
                              <Tag color="blue" style={{ fontSize: 12 }}>{cert}</Tag>
                            </List.Item>
                          )}
                        />
                      </div>
                    )}
                    {result.qualification.required_experience && (
                      <div>
                        <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>业绩要求</Text>
                        <Text style={{ fontSize: 13 }}>{result.qualification.required_experience}</Text>
                      </div>
                    )}
                    {result.qualification.team_requirements && (
                      <div>
                        <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>人员要求</Text>
                        <Text style={{ fontSize: 13 }}>{result.qualification.team_requirements}</Text>
                      </div>
                    )}
                    {result.qualification.financial_requirements && (
                      <div>
                        <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>财务要求</Text>
                        <Text style={{ fontSize: 13 }}>{result.qualification.financial_requirements}</Text>
                      </div>
                    )}
                    {result.qualification.exclusion_conditions && result.qualification.exclusion_conditions.length > 0 && (
                      <div>
                        <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 6 }}>否决条件</Text>
                        <List
                          size="small"
                          dataSource={result.qualification.exclusion_conditions}
                          renderItem={(cond) => (
                            <List.Item style={{ padding: '4px 0' }}>
                              <Text style={{ fontSize: 12, color: '#ef4444' }}>✗ {cond}</Text>
                            </List.Item>
                          )}
                        />
                      </div>
                    )}
                  </div>
                ) : (
                  <Text type="secondary" style={{ fontSize: 12 }}>未解析到资质要求</Text>
                ),
              },
              {
                key: 'scoring',
                label: (
                  <Space size={4}>
                    <BarChartOutlined />
                    评分标准
                  </Space>
                ),
                children: result.scoring ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                      {result.scoring.method && (
                        <div>
                          <Text type="secondary" style={{ fontSize: 12 }}>评标方法</Text>
                          <div><Tag color="blue">{result.scoring.method}</Tag></div>
                        </div>
                      )}
                      {result.scoring.technical_score !== undefined && (
                        <div>
                          <Text type="secondary" style={{ fontSize: 12 }}>技术分</Text>
                          <div><Tag color="purple">{result.scoring.technical_score} 分</Tag></div>
                        </div>
                      )}
                      {result.scoring.commercial_score !== undefined && (
                        <div>
                          <Text type="secondary" style={{ fontSize: 12 }}>商务分</Text>
                          <div><Tag color="orange">{result.scoring.commercial_score} 分</Tag></div>
                        </div>
                      )}
                      {result.scoring.price_score !== undefined && (
                        <div>
                          <Text type="secondary" style={{ fontSize: 12 }}>价格分</Text>
                          <div><Tag color="green">{result.scoring.price_score} 分</Tag></div>
                        </div>
                      )}
                    </div>
                    {result.scoring.details && result.scoring.details.length > 0 ? (
                      <Table
                        size="small"
                        columns={scoringColumns}
                        dataSource={result.scoring.details.map((d, i) => ({ ...d, key: i }))}
                        pagination={false}
                        scroll={{ y: 300 }}
                      />
                    ) : (
                      <Text type="secondary" style={{ fontSize: 12 }}>暂无评分明细</Text>
                    )}
                  </div>
                ) : (
                  <Text type="secondary" style={{ fontSize: 12 }}>未解析到评分标准</Text>
                ),
              },
              {
                key: 'risk',
                label: (
                  <Space size={4}>
                    <WarningOutlined style={{ color: '#f59e0b' }} />
                    <span style={{ color: result.risk_alerts && result.risk_alerts.length > 0 ? '#ef4444' : undefined }}>
                      废标风险
                      {result.risk_alerts && result.risk_alerts.length > 0 && (
                        <Tag color="error" style={{ marginLeft: 4, fontSize: 11 }}>
                          {result.risk_alerts.length}
                        </Tag>
                      )}
                    </span>
                  </Space>
                ),
                children: result.risk_alerts && result.risk_alerts.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {result.risk_alerts.map((alert, i) => (
                      <Alert
                        key={i}
                        type="warning"
                        showIcon
                        message={<span>⚠️ {alert}</span>}
                        style={{ borderColor: '#fbbf24' }}
                      />
                    ))}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '20px 0' }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>✓ 未发现明显废标风险</Text>
                  </div>
                ),
              },
            ]}
          />

          {/* Action Buttons */}
          {result.bid_document_requirements?.chapters && result.bid_document_requirements.chapters.length > 0 && (
            <div style={{
              marginTop: 16,
              padding: '12px 16px',
              background: '#eff6ff',
              borderRadius: 8,
              border: '1px solid #bfdbfe',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 12,
            }}>
              <div>
                <Text strong style={{ fontSize: 13 }}>解析到 {result.bid_document_requirements.chapters.length} 个章节建议</Text>
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {result.bid_document_requirements.chapters.slice(0, 3).join('、')}
                    {result.bid_document_requirements.chapters.length > 3 && ` 等`}
                  </Text>
                </div>
              </div>
              <Button
                type="primary"
                size="small"
                loading={generating}
                disabled={!projectId || !docInfo?.id}
                style={{ background: 'linear-gradient(135deg, #0d9488, #14b8a6)', border: 'none', flexShrink: 0 }}
                icon={<ThunderboltOutlined />}
                onClick={async () => {
                  if (!projectId || !docInfo?.id) {
                    message.warning('缺少项目或招标文件信息');
                    return;
                  }
                  setGenerating(true);
                  setGenProgress({ phase: 'extract', message: '准备 AI 抽取章节模板...', sectionsCreated: 0 });
                  let extractFailed = false;

                  await generateFrameworkFromTender(
                    projectId,
                    docInfo.id,
                    (count) => {
                      setGenProgress({ phase: 'extract', message: `AI 抽取 ${count} 个章节模板中（约 30~60 秒）...`, sectionsCreated: 0 });
                    },
                    (matched, ms) => {
                      setGenProgress({ phase: 'create', message: `AI 抽取完成（命中 ${matched} 个，耗时 ${Math.round(ms / 1000)}s），正在创建章节...`, sectionsCreated: 0 });
                    },
                    (msg, ms) => {
                      extractFailed = true;
                      setGenProgress({ phase: 'create', message: `AI 抽取失败（${msg}，耗时 ${Math.round(ms / 1000)}s），降级创建空章节...`, sectionsCreated: 0 });
                    },
                    (_title, _type, _hasContent) => {
                      setGenProgress((prev) => prev ? { ...prev, sectionsCreated: prev.sectionsCreated + 1 } : prev);
                    },
                    (total, withContent) => {
                      setGenProgress({ phase: 'done', message: `已生成 ${total} 个章节（含模板 ${withContent} 个）`, sectionsCreated: total });
                      setGenerating(false);
                      if (extractFailed) {
                        message.warning(`已创建 ${total} 个空章节框架，AI 模板抽取失败请手动填写`);
                      } else {
                        message.success(`已生成 ${total} 个章节，其中 ${withContent} 个含招标文件模板原文`);
                      }
                      if (onFrameworkGenerated) onFrameworkGenerated(total, withContent);
                    },
                    (errMsg) => {
                      setGenerating(false);
                      setGenProgress(null);
                      message.error(`生成失败: ${errMsg}`);
                    },
                  );
                }}
              >
                {generating ? '生成中...' : '一键填入招标信息'}
              </Button>
            </div>
          )}

          {genProgress && (
            <div style={{
              marginTop: 8,
              padding: '10px 14px',
              background: genProgress.phase === 'done' ? '#f0fdfa' : '#fef3c7',
              borderRadius: 6,
              border: `1px solid ${genProgress.phase === 'done' ? '#99f6e4' : '#fde68a'}`,
              fontSize: 12,
              color: '#475569',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {generating && <Spin size="small" />}
                <span>{genProgress.message}</span>
              </div>
              {genProgress.phase === 'create' && genProgress.sectionsCreated > 0 && (
                <div style={{ marginTop: 4, color: '#0d9488' }}>
                  已创建 {genProgress.sectionsCreated} 个章节
                </div>
              )}
            </div>
          )}

          {/* 保存到招标信息 */}
          <div style={{
            marginTop: 16,
            padding: '12px 16px',
            background: '#f0fdfa',
            borderRadius: 8,
            border: '1px solid #ccfbf1',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
          }}>
            <div>
              <Text strong style={{ fontSize: 13 }}>保存解析结果</Text>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  将项目名称、招标编号、预算金额、时间节点等信息保存到招标管理
                </Text>
              </div>
            </div>
            <Button
              type="primary"
              size="small"
              style={{ background: 'linear-gradient(135deg, #0d9488, #14b8a6)', border: 'none', flexShrink: 0 }}
              onClick={async () => {
                if (!docInfo?.id) return;
                try {
                  const res = await saveToTender(docInfo.id);
                  const action = res.data.action === 'updated' ? '已更新' : '已创建';
                  message.success(`${action}招标信息，更新了 ${res.data.fields_updated.length} 个字段`);
                } catch {
                  // error handled by interceptor
                }
              }}
            >
              保存到招标信息
            </Button>
          </div>

          {/* Bid document requirements summary */}
          {result.bid_document_requirements && (
            result.bid_document_requirements.format ||
            result.bid_document_requirements.copies ||
            result.bid_document_requirements.seal_requirements
          ) && (
            <div style={{ marginTop: 12 }}>
              <Title level={5} style={{ fontSize: 13, marginBottom: 8 }}>标书编制要求</Title>
              <Descriptions column={1} size="small" bordered>
                {result.bid_document_requirements.format && (
                  <Descriptions.Item label="文件格式">{result.bid_document_requirements.format}</Descriptions.Item>
                )}
                {result.bid_document_requirements.copies && (
                  <Descriptions.Item label="份数">{result.bid_document_requirements.copies}</Descriptions.Item>
                )}
                {result.bid_document_requirements.seal_requirements && (
                  <Descriptions.Item label="盖章要求">{result.bid_document_requirements.seal_requirements}</Descriptions.Item>
                )}
              </Descriptions>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
