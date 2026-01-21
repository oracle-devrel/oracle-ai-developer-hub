"use client"

import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism"
import { Copy, Check } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface MessageMarkdownProps {
  content: string
}

export function MessageMarkdown({ content }: MessageMarkdownProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ node, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || "")
          const isInline = !match && !className

          if (isInline) {
            return (
              <code
                className="rounded bg-muted px-1.5 py-0.5 font-mono text-sm"
                {...props}
              >
                {children}
              </code>
            )
          }

          return (
            <CodeBlock
              language={match ? match[1] : "text"}
              value={String(children).replace(/\n$/, "")}
            />
          )
        },
        pre({ children }) {
          // Just return children since CodeBlock handles the wrapper
          return <>{children}</>
        },
        p({ children }) {
          return <p className="mb-2 last:mb-0">{children}</p>
        },
        ul({ children }) {
          return <ul className="mb-2 list-disc pl-4 last:mb-0">{children}</ul>
        },
        ol({ children }) {
          return <ol className="mb-2 list-decimal pl-4 last:mb-0">{children}</ol>
        },
        li({ children }) {
          return <li className="mb-1">{children}</li>
        },
        h1({ children }) {
          return <h1 className="mb-2 text-xl font-bold">{children}</h1>
        },
        h2({ children }) {
          return <h2 className="mb-2 text-lg font-bold">{children}</h2>
        },
        h3({ children }) {
          return <h3 className="mb-2 text-base font-bold">{children}</h3>
        },
        blockquote({ children }) {
          return (
            <blockquote className="mb-2 border-l-2 border-muted-foreground/30 pl-4 italic">
              {children}
            </blockquote>
          )
        },
        a({ href, children }) {
          return (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline underline-offset-2 hover:no-underline"
            >
              {children}
            </a>
          )
        },
        table({ children }) {
          return (
            <div className="mb-2 overflow-x-auto">
              <table className="min-w-full border-collapse">{children}</table>
            </div>
          )
        },
        thead({ children }) {
          return <thead className="bg-muted">{children}</thead>
        },
        th({ children }) {
          return (
            <th className="border border-border px-3 py-2 text-left font-medium">
              {children}
            </th>
          )
        },
        td({ children }) {
          return <td className="border border-border px-3 py-2">{children}</td>
        },
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

interface CodeBlockProps {
  language: string
  value: string
}

function CodeBlock({ language, value }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="group relative mb-2 overflow-hidden rounded-lg">
      <div className="flex items-center justify-between bg-zinc-800 px-4 py-2 text-xs text-zinc-400">
        <span>{language}</span>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 gap-1 px-2 text-xs opacity-0 transition-opacity group-hover:opacity-100"
          onClick={copyToClipboard}
        >
          {copied ? (
            <>
              <Check className="h-3 w-3" />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              Copy
            </>
          )}
        </Button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        customStyle={{
          margin: 0,
          borderRadius: 0,
          padding: "1rem",
        }}
      >
        {value}
      </SyntaxHighlighter>
    </div>
  )
}
