/** 预览仅从 Markdown 原文派生，关闭原始 HTML，并在插入页面前清理 HTML。 */
import MarkdownIt from 'markdown-it'
import taskLists from 'markdown-it-task-lists'
import DOMPurify from 'dompurify'
import highlight from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'
import sql from 'highlight.js/lib/languages/sql'

// 常用研发语言按需注册；其他语言仍显示完整代码，不影响 Markdown 原文。
highlight.registerLanguage('python', python)
highlight.registerLanguage('javascript', javascript)
highlight.registerLanguage('typescript', typescript)
highlight.registerLanguage('json', json)
highlight.registerLanguage('bash', bash)
highlight.registerLanguage('sql', sql)

const markdown = new MarkdownIt({
  html: false,
  breaks: false,
  highlight(code, language) {
    if (language && highlight.getLanguage(language)) {
      return highlight.highlight(code, { language, ignoreIllegals: true }).value
    }
    return ''
  },
}).use(taskLists)

export function renderMarkdown(source: string): string {
  return DOMPurify.sanitize(markdown.render(source))
}
