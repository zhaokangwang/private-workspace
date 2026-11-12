/** 工具栏直接修改 CodeMirror 选区，保留撤销记录；不另存一份 Markdown 正文。 */
import type { EditorView } from '@codemirror/view'
import { redo, undo } from '@codemirror/commands'

export type FormatCommand =
  | 'heading'
  | 'bold'
  | 'italic'
  | 'list'
  | 'task'
  | 'quote'
  | 'link'
  | 'code'
  | 'table'
  | 'undo'
  | 'redo'

function wrapSelection(view: EditorView, before: string, after: string, placeholder: string): void {
  const { from, to } = view.state.selection.main
  const selected = view.state.sliceDoc(from, to) || placeholder
  view.dispatch({
    changes: { from, to, insert: before + selected + after },
    selection: { anchor: from + before.length, head: from + before.length + selected.length },
    scrollIntoView: true,
  })
}

function prefixLines(view: EditorView, prefix: string): void {
  const { from, to } = view.state.selection.main
  const first = view.state.doc.lineAt(from)
  const last = view.state.doc.lineAt(to > from ? to - 1 : to)
  const text = view.state.sliceDoc(first.from, last.to)
  const insert = text
    .split('\n')
    .map((line) => prefix + line)
    .join('\n')
  view.dispatch({
    changes: { from: first.from, to: last.to, insert },
    selection: { anchor: first.from + insert.length },
  })
}

export function applyFormat(view: EditorView, command: FormatCommand): void {
  switch (command) {
    case 'heading':
      prefixLines(view, '## ')
      break
    case 'bold':
      wrapSelection(view, '**', '**', '加粗文字')
      break
    case 'italic':
      wrapSelection(view, '*', '*', '斜体文字')
      break
    case 'list':
      prefixLines(view, '- ')
      break
    case 'task':
      prefixLines(view, '- [ ] ')
      break
    case 'quote':
      prefixLines(view, '> ')
      break
    case 'link':
      wrapSelection(view, '[', '](https://example.com)', '链接文字')
      break
    case 'code':
      wrapSelection(view, '\n```\n', '\n```\n', '代码')
      break
    case 'table':
      wrapSelection(view, '\n', '\n', '| 列名 | 列名 |\n| --- | --- |\n| 内容 | 内容 |')
      break
    case 'undo':
      undo(view)
      break
    case 'redo':
      redo(view)
      break
  }
  view.focus()
}
