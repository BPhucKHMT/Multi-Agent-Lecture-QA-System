import { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, Terminal, AlertCircle, Code } from 'lucide-react';
import { buildCitationItems, buildCitationItemsFromContext } from '../../lib/utils/citation';
import type { RagResponse } from '../../types/rag';

type MarkdownRendererProps = {
  content: string;
  response?: RagResponse;
  tempContext?: any[];
  className?: string;
  isStreaming?: boolean;
};

const CodeBlock = ({ language, value }: { language: string; value: string }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isOutput = language === 'output';
  const isError = language === 'error';
  const isTerminal = isOutput || isError;

  return (
    <div className={`not-prose group relative my-6 overflow-hidden rounded-2xl border shadow-lg transition-all duration-300 
      ${isOutput ? 'border-emerald-500/20 bg-[#0d1117] shadow-emerald-500/5' : 
        isError ? 'border-rose-500/20 bg-[#0d1117] shadow-rose-500/5' : 
        'border-violet-100/50 bg-[#1e1e1e] shadow-violet-500/5'}`}>
      
      {/* Header */}
      <div className={`flex items-center justify-between px-4 py-2.5 border-b 
        ${isOutput ? 'bg-emerald-500/5 border-emerald-500/10' : 
          isError ? 'bg-rose-500/5 border-rose-500/10' : 
          'bg-[#252526] border-white/5'}`}>
        
        <div className="flex items-center gap-3">
          {isTerminal && (
            <div className="flex gap-1.5">
              <div className="h-2.5 w-2.5 rounded-full bg-[#ff5f56]" />
              <div className="h-2.5 w-2.5 rounded-full bg-[#ffbd2e]" />
              <div className="h-2.5 w-2.5 rounded-full bg-[#27c93f]" />
            </div>
          )}
          <div className="flex items-center gap-2">
            {isOutput ? (
              <Terminal className="h-3.5 w-3.5 text-emerald-400" />
            ) : isError ? (
              <AlertCircle className="h-3.5 w-3.5 text-rose-400" />
            ) : (
              <Code className="h-3.5 w-3.5 text-violet-400" />
            )}
            <span className={`text-[11px] font-black uppercase tracking-widest 
              ${isOutput ? 'text-emerald-400/80' : 
                isError ? 'text-rose-400/80' : 
                'text-slate-400'}`}>
              {isOutput ? 'Terminal Output' : isError ? 'Execution Error' : (language || 'code')}
            </span>
          </div>
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-[11px] font-bold text-slate-400 transition-all hover:bg-white/5 hover:text-white active:scale-95"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-emerald-400" />
              <span className="text-emerald-400">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Content */}
      <div className="p-1">
        <SyntaxHighlighter
          language={isTerminal ? 'text' : (language || 'text')}
          style={vscDarkPlus}
          customStyle={{
            margin: 0,
            padding: '1.25rem',
            background: 'transparent',
            fontSize: '13 px',
            lineHeight: '1.6',
          }}
          codeTagProps={{
            style: {
              fontFamily: '"Fira Code", monospace',
              color: isOutput ? '#10b981' : isError ? '#f43f5e' : undefined,
            }
          }}
        >
          {value}
        </SyntaxHighlighter>
      </div>
    </div>
  );
};

export default function MarkdownRenderer({ 
  content, 
  response, 
  tempContext,
  className = "",
  isStreaming = false
}: MarkdownRendererProps) {

  const processedContent = useMemo(() => {
    return content.replace(/\[(\d+)\]/g, (match, p1) => {
      return `[${match}](cite:${p1})`;
    });
  }, [content]);

  const citations = useMemo(() => {
    if (response) return buildCitationItems(content, response);
    if (tempContext && tempContext.length > 0) return buildCitationItemsFromContext(content, tempContext);
    return [];
  }, [content, response, tempContext]);

  const displayContent = useMemo(() => {
    let fixed = processedContent;
    const codeBlockMatches = fixed.match(/```/g) || [];
    if (codeBlockMatches.length % 2 !== 0) {
      fixed += "\n```";
    }
    const mathDelimiterMatches = fixed.match(/(?<!\\)\$/g) || [];
    if (mathDelimiterMatches.length % 2 !== 0) {
      fixed += "$";
    }
    const boldMatches = fixed.match(/(?<!\\)\*\*/g) || [];
    if (boldMatches.length % 2 !== 0) {
       fixed += "**";
    }
    return fixed;
  }, [processedContent]);

  return (
    <div className="relative">
      <div className={`prose prose-slate prose-base max-w-none 
      prose-headings:font-bold prose-headings:text-slate-900 
      prose-p:leading-[1.75] prose-p:text-slate-800 prose-p:my-4
      prose-strong:font-bold prose-strong:text-violet-950
      prose-ul:my-4 prose-ul:list-disc prose-ul:pl-6
      prose-ol:my-4 prose-ol:list-decimal prose-ol:pl-6
      prose-li:my-1.5 prose-li:leading-relaxed
      prose-a:text-violet-600 prose-a:no-underline hover:prose-a:underline
      prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:bg-slate-100 prose-code:text-violet-600 prose-code:before:content-none prose-code:after:content-none prose-code:break-words prose-code:whitespace-pre-wrap
      prose-pre:bg-transparent prose-pre:p-0 prose-pre:my-0
      ${className}`}>
      <ReactMarkdown 
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const isInline = !className;
            
            if (!isInline && match) {
              return (
                <CodeBlock 
                  language={match[1]} 
                  value={String(children).replace(/\n$/, '')} 
                />
              );
            }
            
            return (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
          a: ({ href, children }) => {
            const isCitation = href?.startsWith('cite:');
            
            if (isCitation) {
              const index = parseInt(href!.split(':')[1], 10);
              const citation = citations.find(c => c.index === index);
              
              if (citation && citation.video_url) {
                return (
                  <a
                    href={citation.video_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mx-0.5 inline-flex items-center justify-center rounded-md bg-violet-100/60 px-1.5 py-0.5 text-[12.5px] font-bold text-violet-700 transition-all hover:bg-violet-600 hover:text-white hover:scale-110 active:scale-95 no-underline decoration-transparent"
                    title={citation.title || "Xem nguồn video"}
                  >
                    {children}
                  </a>
                );
              }
              return (
                <span className="mx-0.5 inline-flex items-center justify-center rounded-md bg-slate-100 px-1.5 py-0.5 text-[12.5px] font-bold text-slate-400 cursor-not-allowed">
                  {children}
                </span>
              );
            }
            
            return (
              <a href={href} target="_blank" rel="noreferrer">
                {children}
              </a>
            );
          }
        }}
      >
        {displayContent}
      </ReactMarkdown>
      {isStreaming && <span className="puq-cursor" aria-hidden="true" />}
    </div>
  </div>
  );
}


