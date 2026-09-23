import React, { useState } from 'react';
import { Copy, Check, Terminal } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const handleCopy = (code: string, index: number) => {
    navigator.clipboard.writeText(code);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Helper to parse inline markdown: **bold**, *italic*, `code`
  const renderInline = (text: string): React.ReactNode => {
    const parts: React.ReactNode[] = [];
    // Regex for bold, italic, code
    const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index));
      }

      const matchText = match[0];
      if (matchText.startsWith('**') && matchText.endsWith('**')) {
        parts.push(
          <strong key={match.index} className="font-semibold text-white">
            {matchText.slice(2, -2)}
          </strong>
        );
      } else if (matchText.startsWith('*') && matchText.endsWith('*')) {
        parts.push(
          <em key={match.index} className="italic text-zinc-300">
            {matchText.slice(1, -1)}
          </em>
        );
      } else if (matchText.startsWith('`') && matchText.endsWith('`')) {
        parts.push(
          <code
            key={match.index}
            className="px-1.5 py-0.5 rounded bg-[#1e1e24] border border-white/10 font-mono text-[11px] text-zinc-200"
          >
            {matchText.slice(1, -1)}
          </code>
        );
      }

      lastIndex = match.index + matchText.length;
    }

    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex));
    }

    return parts;
  };

  // Parse lines into blocks: code blocks, headings, lists, paragraphs
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBlockContent: string[] = [];
  let codeBlockLang = '';
  let blockIndex = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith('```')) {
      if (!inCodeBlock) {
        inCodeBlock = true;
        codeBlockLang = line.slice(3).trim() || 'text';
        codeBlockContent = [];
      } else {
        inCodeBlock = false;
        const codeText = codeBlockContent.join('\n');
        const curIdx = blockIndex++;
        elements.push(
          <div
            key={`code-${curIdx}`}
            className="my-2.5 rounded-xl border border-[#27272a] bg-[#0c0c0e] overflow-hidden shadow-md font-mono text-[11px]"
          >
            <div className="px-3 py-1.5 bg-[#141417] border-b border-[#27272a] flex items-center justify-between text-zinc-400 select-none">
              <div className="flex items-center gap-1.5">
                <Terminal className="w-3 h-3 text-zinc-400" />
                <span className="text-[10px] uppercase font-bold text-zinc-300">{codeBlockLang}</span>
              </div>
              <button
                onClick={() => handleCopy(codeText, curIdx)}
                className="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-white transition-colors"
                title="Copy code"
              >
                {copiedIndex === curIdx ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
            <pre className="p-3 overflow-x-auto text-zinc-300 leading-relaxed font-mono">
              <code>{codeText}</code>
            </pre>
          </div>
        );
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockContent.push(line);
      continue;
    }

    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }

    // Headings
    if (trimmed.startsWith('#### ')) {
      elements.push(
        <h4 key={`h4-${i}`} className="text-xs font-bold text-white mt-3 mb-1 flex items-center gap-1.5">
          {renderInline(trimmed.slice(5))}
        </h4>
      );
    } else if (trimmed.startsWith('### ')) {
      elements.push(
        <h3 key={`h3-${i}`} className="text-sm font-bold text-white mt-3.5 mb-1.5 flex items-center gap-2 border-b border-[#27272a] pb-1">
          {renderInline(trimmed.slice(4))}
        </h3>
      );
    } else if (trimmed.startsWith('## ')) {
      elements.push(
        <h2 key={`h2-${i}`} className="text-sm font-bold text-white mt-4 mb-2 pb-1 border-b border-[#27272a]">
          {renderInline(trimmed.slice(3))}
        </h2>
      );
    } else if (trimmed.startsWith('* ') || trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
      // Bullet list item
      elements.push(
        <div key={`li-${i}`} className="flex items-start gap-2 my-1 text-zinc-300 text-xs">
          <span className="text-zinc-500 font-bold text-[13px] leading-none mt-0.5">•</span>
          <div className="flex-1 leading-relaxed">{renderInline(trimmed.slice(2))}</div>
        </div>
      );
    } else if (/^\d+\.\s/.test(trimmed)) {
      // Numbered list item
      const match = trimmed.match(/^(\d+)\.\s(.*)$/);
      if (match) {
        elements.push(
          <div key={`nli-${i}`} className="flex items-start gap-2 my-1 text-zinc-300 text-xs">
            <span className="text-zinc-400 font-mono font-bold text-[11px] mt-0.5">{match[1]}.</span>
            <div className="flex-1 leading-relaxed">{renderInline(match[2])}</div>
          </div>
        );
      }
    } else {
      // Regular paragraph
      elements.push(
        <p key={`p-${i}`} className="my-1.5 text-zinc-200 text-xs leading-relaxed">
          {renderInline(trimmed)}
        </p>
      );
    }
  }

  return <div className="space-y-0.5">{elements}</div>;
};
