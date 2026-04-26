import { useEffect, useRef } from 'react';
import { useEditor, EditorContent, Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Table } from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import TableCell from '@tiptap/extension-table-cell';
import TableHeader from '@tiptap/extension-table-header';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import { Markdown } from 'tiptap-markdown';
import { Button, Tooltip, Space, Divider } from 'antd';
import {
  BoldOutlined, ItalicOutlined, OrderedListOutlined, UnorderedListOutlined,
  UndoOutlined, RedoOutlined, TableOutlined, StrikethroughOutlined,
  LinkOutlined,
} from '@ant-design/icons';

interface Props {
  value: string;
  onChange: (markdown: string) => void;
  placeholder?: string;
  minHeight?: number | string;
}

/** 表格上下补空行，避免 markdown 解析器把表格上下文吃进表格 */
function normalizeMd(text: string): string {
  if (!text) return text;
  let out = text.replace(/(^\|[^\n]*\|)\n(?!\n|\|)/gm, '$1\n\n');
  out = out.replace(/(^[^|\n][^\n]*)\n(\|[^\n]*\|)/gm, '$1\n\n$2');
  return out.replace(/\n{3,}/g, '\n\n');
}

/** 工具栏按钮 */
function ToolbarButton({
  active, disabled, icon, tip, onClick,
}: { active?: boolean; disabled?: boolean; icon: React.ReactNode; tip: string; onClick: () => void }) {
  return (
    <Tooltip title={tip}>
      <Button
        type={active ? 'primary' : 'text'}
        size="small"
        disabled={disabled}
        icon={icon}
        onClick={onClick}
        style={active ? { background: '#0d9488', borderColor: '#0d9488' } : undefined}
      />
    </Tooltip>
  );
}

function HeadingButton({ editor, level }: { editor: Editor; level: 1 | 2 | 3 }) {
  const active = editor.isActive('heading', { level });
  return (
    <Tooltip title={`H${level} 标题`}>
      <Button
        type={active ? 'primary' : 'text'}
        size="small"
        onClick={() => editor.chain().focus().toggleHeading({ level }).run()}
        style={active ? { background: '#0d9488', borderColor: '#0d9488' } : undefined}
      >
        H{level}
      </Button>
    </Tooltip>
  );
}

export default function RichTextEditor({ value, onChange, placeholder, minHeight = 480 }: Props) {
  const lastEmittedRef = useRef<string>('');

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // StarterKit 会自带 Table 之外的大部分常用扩展
        heading: { levels: [1, 2, 3] },
      }),
      Table.configure({ resizable: true, HTMLAttributes: { class: 'tiptap-table' } }),
      TableRow,
      TableHeader,
      TableCell,
      Link.configure({ openOnClick: false, HTMLAttributes: { rel: 'noopener noreferrer', target: '_blank' } }),
      Placeholder.configure({ placeholder: placeholder || '在此输入章节内容...' }),
      Markdown.configure({
        html: false,           // 不接受 raw HTML（更可控）
        tightLists: true,      // 列表紧凑
        bulletListMarker: '-', // 用 - 作为无序列表标记
        linkify: false,
        breaks: false,
        transformPastedText: true,
        transformCopiedText: true,
      }),
    ],
    content: normalizeMd(value || ''),
    onUpdate: ({ editor }) => {
      const md = (editor.storage as any).markdown.getMarkdown() as string;
      lastEmittedRef.current = md;
      onChange(md);
    },
  });

  // 外部 value 变化时同步到编辑器（避免回环：仅当外部值与最后一次发出的不同才更新）
  useEffect(() => {
    if (!editor) return;
    if (value === lastEmittedRef.current) return;
    editor.commands.setContent(normalizeMd(value || ''), { emitUpdate: false });
    lastEmittedRef.current = value;
  }, [value, editor]);

  if (!editor) return null;

  const insertTable = () => {
    editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
  };

  const setLink = () => {
    const previousUrl = editor.getAttributes('link').href;
    const url = window.prompt('请输入链接地址', previousUrl || 'https://');
    if (url === null) return;
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run();
      return;
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
  };

  return (
    <div style={{ border: '1px solid #d9d9d9', borderRadius: 6, background: '#fff' }}>
      {/* 工具栏 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 4,
          padding: '6px 10px',
          borderBottom: '1px solid #e5e7eb',
          background: '#fafafa',
          borderRadius: '6px 6px 0 0',
        }}
      >
        <Space size={2} wrap>
          <HeadingButton editor={editor} level={1} />
          <HeadingButton editor={editor} level={2} />
          <HeadingButton editor={editor} level={3} />
          <Divider type="vertical" style={{ margin: '0 4px' }} />
          <ToolbarButton tip="加粗" icon={<BoldOutlined />} active={editor.isActive('bold')}
            onClick={() => editor.chain().focus().toggleBold().run()} />
          <ToolbarButton tip="斜体" icon={<ItalicOutlined />} active={editor.isActive('italic')}
            onClick={() => editor.chain().focus().toggleItalic().run()} />
          <ToolbarButton tip="删除线" icon={<StrikethroughOutlined />} active={editor.isActive('strike')}
            onClick={() => editor.chain().focus().toggleStrike().run()} />
          <Divider type="vertical" style={{ margin: '0 4px' }} />
          <ToolbarButton tip="无序列表" icon={<UnorderedListOutlined />} active={editor.isActive('bulletList')}
            onClick={() => editor.chain().focus().toggleBulletList().run()} />
          <ToolbarButton tip="有序列表" icon={<OrderedListOutlined />} active={editor.isActive('orderedList')}
            onClick={() => editor.chain().focus().toggleOrderedList().run()} />
          <Divider type="vertical" style={{ margin: '0 4px' }} />
          <ToolbarButton tip="插入表格（3x3）" icon={<TableOutlined />} onClick={insertTable} />
          <ToolbarButton tip="超链接" icon={<LinkOutlined />} active={editor.isActive('link')} onClick={setLink} />
          {editor.isActive('table') && (
            <>
              <Divider type="vertical" style={{ margin: '0 4px' }} />
              <Tooltip title="表格上方加行">
                <Button size="small" type="text" onClick={() => editor.chain().focus().addRowBefore().run()}>↑行</Button>
              </Tooltip>
              <Tooltip title="表格下方加行">
                <Button size="small" type="text" onClick={() => editor.chain().focus().addRowAfter().run()}>↓行</Button>
              </Tooltip>
              <Tooltip title="左侧加列">
                <Button size="small" type="text" onClick={() => editor.chain().focus().addColumnBefore().run()}>←列</Button>
              </Tooltip>
              <Tooltip title="右侧加列">
                <Button size="small" type="text" onClick={() => editor.chain().focus().addColumnAfter().run()}>列→</Button>
              </Tooltip>
              <Tooltip title="删除当前行">
                <Button size="small" type="text" danger onClick={() => editor.chain().focus().deleteRow().run()}>删行</Button>
              </Tooltip>
              <Tooltip title="删除当前列">
                <Button size="small" type="text" danger onClick={() => editor.chain().focus().deleteColumn().run()}>删列</Button>
              </Tooltip>
              <Tooltip title="删除整个表格">
                <Button size="small" type="text" danger onClick={() => editor.chain().focus().deleteTable().run()}>删表</Button>
              </Tooltip>
            </>
          )}
        </Space>
        <div style={{ flex: 1 }} />
        <Space size={2}>
          <ToolbarButton tip="撤销" icon={<UndoOutlined />} disabled={!editor.can().undo()}
            onClick={() => editor.chain().focus().undo().run()} />
          <ToolbarButton tip="重做" icon={<RedoOutlined />} disabled={!editor.can().redo()}
            onClick={() => editor.chain().focus().redo().run()} />
        </Space>
      </div>

      {/* 编辑区 */}
      <div
        className="tiptap-wrapper"
        style={{
          padding: '12px 16px',
          minHeight,
          fontSize: 14,
          lineHeight: 1.8,
        }}
      >
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}
