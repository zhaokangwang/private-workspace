import { describe, expect, it } from 'vitest'
import { renderMarkdown } from '@/markdown/render'

describe('Markdown 预览', () => {
  it('支持标题、表格、任务列表和代码块', () => {
    const html = renderMarkdown(
      '## 今日完成\n\n- [x] 接入 API\n\n| 项目 | 状态 |\n| --- | --- |\n| 日报 | 完成 |\n\n```python\nprint("hello")\n```',
    )
    expect(html).toContain('<h2>今日完成</h2>')
    expect(html).toContain('<table>')
    expect(html).toContain('type="checkbox"')
    expect(html).toContain('disabled')
    expect(html).toContain('hljs-built_in')
  })
  it('原始 HTML 作为文本，危险链接不能执行', () => {
    const html = renderMarkdown(
      '<img src=x onerror=alert(1)>\n<script>alert(1)</script>\n\n[危险](javascript:alert(1))',
    )
    const element = document.createElement('div')
    element.innerHTML = html
    expect(element.querySelector('script, img, [onerror]')).toBeNull()
    expect(element.querySelector('a[href^="javascript:"]')).toBeNull()
    expect(element.textContent).toContain('<script>')
  })
})
