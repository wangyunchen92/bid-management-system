import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { LIBRARY_API } from '@/constants/api';

interface Props {
  content: string;
  /** 容器自定义样式 */
  style?: React.CSSProperties;
  /** 紧凑模式，标题/段落间距更小 */
  compact?: boolean;
}

const ATTACHMENT_RE = /\[附件:([^:\]]+):([^\]]+)\]/g;

function AttachmentLink({ filePath, fileName }: { filePath: string; fileName: string }) {
  const ext = filePath.split('.').pop()?.toLowerCase();
  const isImage = ['jpg', 'jpeg', 'png', 'webp', 'gif'].includes(ext || '');
  return (
    <a
      href={LIBRARY_API.FILE_URL(filePath)}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 8px',
        background: '#f0fdfa',
        border: '1px solid #99f6e4',
        borderRadius: 4,
        color: '#0d9488',
        fontSize: 13,
        textDecoration: 'none',
        margin: '2px 0',
      }}
    >
      {isImage ? '🖼' : '📄'} {fileName}
      <span style={{ fontSize: 11, color: '#94a3b8' }}>（点击查看）</span>
    </a>
  );
}

/** 用 [附件:...] 标记切分内容 → 每段内容用 markdown 渲染、附件单独渲染为链接 */
export default function MarkdownContent({ content, style, compact }: Props) {
  if (!content) return null;

  const segments: React.ReactNode[] = [];
  let lastIdx = 0;
  let i = 0;
  for (const m of content.matchAll(ATTACHMENT_RE)) {
    const idx = m.index ?? 0;
    if (idx > lastIdx) {
      segments.push(<MdBlock key={`md-${i}`} text={content.slice(lastIdx, idx)} />);
    }
    segments.push(<AttachmentLink key={`att-${i}`} filePath={m[1]} fileName={m[2]} />);
    lastIdx = idx + m[0].length;
    i += 1;
  }
  if (lastIdx < content.length) {
    segments.push(<MdBlock key={`md-${i}`} text={content.slice(lastIdx)} />);
  }
  if (segments.length === 0) {
    segments.push(<MdBlock key="md-only" text={content} />);
  }

  return (
    <div className={`md-content${compact ? ' md-content-compact' : ''}`} style={style}>
      {segments}
    </div>
  );
}

/** 规范化 markdown：确保表格首行前、末行后各有空行，避免跟正文粘连 */
function normalizeMarkdown(text: string): string {
  // 表格末尾「| ... |」后紧跟非 |/非空行 → 插入空行
  let out = text.replace(/(^\|[^\n]*\|)(\n)(?!\n|\|)/gm, '$1\n\n');
  // 非空非 | 行紧跟「| ... |」首行 → 插入空行
  out = out.replace(/([^\n|])\n(\|[^\n]*\|)/g, '$1\n\n$2');
  return out;
}

function MdBlock({ text }: { text: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        table: ({ node, ...props }) => (
          <div style={{ overflowX: 'auto', margin: '12px 0' }}>
            <table
              style={{
                borderCollapse: 'collapse',
                width: '100%',
                fontSize: 13,
                background: '#fff',
              }}
              {...props}
            />
          </div>
        ),
        th: ({ node, ...props }) => (
          <th
            style={{
              border: '1px solid #cbd5e1',
              padding: '6px 10px',
              background: '#f1f5f9',
              textAlign: 'left',
              fontWeight: 600,
              color: '#0f172a',
              whiteSpace: 'pre-wrap',
            }}
            {...props}
          />
        ),
        td: ({ node, ...props }) => (
          <td
            style={{
              border: '1px solid #cbd5e1',
              padding: '6px 10px',
              verticalAlign: 'top',
              whiteSpace: 'pre-wrap',
              color: '#1e293b',
            }}
            {...props}
          />
        ),
        h1: ({ node, ...props }) => (
          <h1 style={{ fontSize: 20, fontWeight: 700, margin: '14px 0 8px', color: '#0f172a' }} {...props} />
        ),
        h2: ({ node, ...props }) => (
          <h2 style={{ fontSize: 17, fontWeight: 700, margin: '12px 0 6px', color: '#0f172a' }} {...props} />
        ),
        h3: ({ node, ...props }) => (
          <h3 style={{ fontSize: 15, fontWeight: 600, margin: '10px 0 4px', color: '#0f172a' }} {...props} />
        ),
        p: ({ node, ...props }) => (
          <p style={{ margin: '6px 0', lineHeight: 1.8, whiteSpace: 'pre-wrap' }} {...props} />
        ),
        ul: ({ node, ...props }) => <ul style={{ margin: '6px 0', paddingLeft: 22, lineHeight: 1.8 }} {...props} />,
        ol: ({ node, ...props }) => <ol style={{ margin: '6px 0', paddingLeft: 22, lineHeight: 1.8 }} {...props} />,
        li: ({ node, ...props }) => <li style={{ margin: '2px 0' }} {...props} />,
        code: ({ node, ...props }) => (
          <code
            style={{
              background: '#f1f5f9',
              padding: '1px 6px',
              borderRadius: 4,
              fontSize: 12,
              color: '#0d9488',
            }}
            {...props}
          />
        ),
        blockquote: ({ node, ...props }) => (
          <blockquote
            style={{
              margin: '8px 0',
              padding: '6px 12px',
              borderLeft: '3px solid #14b8a6',
              background: '#f0fdfa',
              color: '#0f172a',
            }}
            {...props}
          />
        ),
        hr: () => <hr style={{ border: 'none', borderTop: '1px solid #e2e8f0', margin: '12px 0' }} />,
      }}
    >
      {normalizeMarkdown(text)}
    </ReactMarkdown>
  );
}
