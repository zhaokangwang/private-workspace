# 私人工作站

个人研发工作记录与 Markdown 日报工作台。前端采用 TypeScript、Vue 3 和 Vite，后端采用 Python 3.13 和 FastAPI，开发规范见 [AGENTS.md](./AGENTS.md)。

当前完成第 4 阶段日报编辑工作台。页面支持打开或创建日报、历史日期补写、分页列表、Markdown 编辑与实时预览、手动版本化保存、未保存切换保护和版本冲突比较。数据由 SQLite 持久化，每次成功保存记录快照。

已完成功能及后续需求见 [功能需求清单](./docs/requirements.md)。第 5 阶段尚未开始。

## 获取项目与版本控制

远程仓库：git@github.com:zhaokangwang/private-workspace.git，主分支为 main。

在新机器上克隆后，按照下文安装依赖并执行数据库迁移。SQLite 运行数据不在仓库中，需要单独备份和迁移。

```powershell
git clone git@github.com:zhaokangwang/private-workspace.git
Set-Location private-workspace
```

日常修改后先执行对应检查，再查看改动并提交需要保存的文件。例如只修改需求文档时：

```powershell
git status
git diff
git add docs/requirements.md
git commit -m "docs: 更新日报功能需求"
git push
```

首次推送会将本地 main 与 origin/main 关联，后续 git push 会推送当前分支。提交前通过 git diff --cached 检查暂存内容；本地 .env、数据库、依赖、构建产物和 IDE 状态由忽略规则排除。

## 环境

- Python 3.13，通过 uv 管理项目虚拟环境和锁定依赖。
- Node.js 22.18 或满足 frontend/package.json 中 engines 约束的版本，使用 npm 管理依赖。
- 后端依赖锁文件为 backend/uv.lock，前端依赖锁文件为 frontend/package-lock.json。

安装依赖后，由 uv run 使用 backend/.venv，日常开发无需手动激活虚拟环境。所有命令都注明执行目录，以下示例使用 PowerShell。

## 安装依赖

在项目根目录执行以下命令。

```powershell
Set-Location D:\appSource\private-workspace\backend
uv sync --locked

Set-Location D:\appSource\private-workspace\frontend
npm ci
```

迁移到其他机器后，将示例中的项目根路径替换为实际路径。

## 初始化 SQLite 数据库

在 backend 目录执行以下命令，应用全部已发布的结构迁移。

```powershell
uv run alembic upgrade head
uv run alembic current
uv run alembic check
```

默认数据库位于项目根目录下的 data/workspace.db。设置从 app/config.py 读取，路径相对项目根目录解析，从 PyCharm 或其他目录启动时保持同一个位置。创建数据库结构使用显式迁移命令，启动 Web 服务时无需重复建表。

需要自定义路径时，将 backend/.env.example 复制为 backend/.env，再调整配置。环境变量优先于 .env，程序显式传入的配置优先级最高。

```dotenv
WORKSPACE_DATA_DIR=data
WORKSPACE_SQLITE_BUSY_TIMEOUT_MS=5000
```

WORKSPACE_DATA_DIR 支持绝对路径。容器部署时可以配置为 /data 并挂载持久化目录。修改该配置会连接新位置的数据库，迁移旧数据需要通过备份和恢复完成。

SQLAlchemy 负责以 Python 对象读写数据，Alembic 负责按版本更新表结构。当前版本为 0001_create_documents。除了业务表，Alembic 会创建 alembic_version 记录已应用的迁移。

### 文档表与历史快照

| 表 | 用途 | 主要字段 |
|---|---|---|
| document | 文档当前内容 | id、document_type、title、period_start、period_end、content_md、version、metadata、created_at、updated_at、deleted_at |
| document_revision | 特定版本的标题与正文快照 | document_id、version、title、content_md、change_source、created_at |

文档类型支持 daily、weekly、monthly。日报起止日期相同，周报从周一到周日，月报从当月第一天到最后一天。数据库约束会检查完整周期，并限制每个周期只有一篇未删除的同类报告。

正文以 Markdown 原文保存。metadata 保存 JSON 对象，ORM 属性名为 document_metadata，以避开 SQLAlchemy 的同名保留属性。修改扩展信息时赋予一个新的字典，例如 document.document_metadata = {"template_key": "daily_default"}。

version 用于保存时的原子版本检查。deleted_at 为空表示正常文档，有值表示移入回收站；已有新日报时，恢复同一天的旧日报会触发唯一性冲突。

快照以 document_id 和 version 联合唯一，change_source 可取 manual、periodic、import、agent、restore。创建日报时记录版本 1 的初始快照，每次成功调用保存接口递增版本并记录 manual 快照。带快照的文档受到外键保护，直接物理删除会失败。恢复正文和其他来源的保存功能将在对应阶段接入。

操作时间在 SQLite 内以 UTC 值保存，ORM 读取时附带 UTC 时区，接口返回带时区的 ISO 8601 字符串；写入时间必须带时区。报告所属日期使用单独的 DATE 字段，接口按 Asia/Shanghai 确定“今天”，Windows 使用 tzdata 提供时区数据。

### 连接与迁移规则

每条 SQLite 连接启用外键、WAL 和写入等待超时，使用 Python 3.13 的明确事务模式。会话在业务操作中按需创建，服务层负责事务提交与回滚。主表更新和快照写入可以在同一个事务中完成，异常时一起回滚。

WAL 运行时可能在数据库旁生成 workspace.db-wal 和 workspace.db-shm，它们属于数据库运行文件。数据目录已经加入 Git 忽略规则。后续备份功能会使用一致性备份，保留运行数据的完整性。

增加或调整字段时，先修改 models.py，再在 backend 目录生成迁移并人工检查 SQL 和数据处理方式。

```powershell
uv run alembic revision --autogenerate -m "说明本次变更"
uv run alembic upgrade head
uv run alembic check
```

迁移脚本是当时结构的独立记录，发布后通过新迁移继续演进。SQLite 的部分改表操作需要重建并复制表，Alembic 已配置 batch 模式。执行真实数据变更前先做可恢复备份。首版迁移的 downgrade 会删除两张业务表及其中的数据，只在明确需要清空的测试库验证。

## 启动后端

在一个终端进入 backend 目录后执行以下命令。

```powershell
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8009
```

- 健康接口为 http://127.0.0.1:8009/api/v1/health。
- 交互式接口文档为 http://127.0.0.1:8009/docs。
- OpenAPI 描述为 http://127.0.0.1:8009/openapi.json。

健康响应包含 status、service 和 version，用于检查后端进程运行状态。数据库结构通过迁移检查验证，数据读写通过文档接口验证。

## 日报核心接口

在 /docs 的“日报文档”分组中可以直接尝试以下四个操作。数据库需要先执行 alembic upgrade head。

| 方法与路径 | 作用 | 主要约定 |
|---|---|---|
| POST /api/v1/daily-reports/open | 打开或创建指定日期的日报 | 首次创建返回 201，已有日报返回 200，传入 {} 使用北京时间的今天 |
| GET /api/v1/documents | 分页查询文档概要 | 默认日报、page=1、page_size=20，按报告开始日期倒序 |
| GET /api/v1/documents/{id} | 读取标题、正文和当前版本 | 已删除或不存在返回 404 |
| PATCH /api/v1/documents/{id} | 按版本保存文档 | expected_version 必填，至少提供 title 或 content_md，版本过期返回 409 |

列表支持 document_type=daily、weekly、monthly，start_date 和 end_date 按报告开始日期筛选，包含边界日期。page_size 范围为 1 到 100，超出当前页数时 items 为空。列表返回 items、total、page、page_size，概要包含标题、周期、版本和时间，正文通过详情接口读取。

保存请求可以只修改标题或正文。标题去掉首尾空白后必须有 1 到 200 个字符，空正文使用空字符串，显式 null 和未约定的字段会被拒绝。日期与文档类型由创建流程确定。输入校验失败返回 422，已有数据保持原样。

下面的 PowerShell 示例可在后端启动后执行，会在当前连接的数据库中创建和修改一篇日报。

```powershell
$apiBase = 'http://127.0.0.1:8009/api/v1'
$openBody = @{ report_date = '2026-11-12' } | ConvertTo-Json
$report = Invoke-RestMethod -Method Post -Uri "$apiBase/daily-reports/open" `
    -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($openBody))

$saveBody = @{
    expected_version = $report.version
    title = '2026-11-12 日报'
    content_md = "## 今日完成`n`n- 验证日报接口`n"
} | ConvertTo-Json
$savedReport = Invoke-RestMethod -Method Patch -Uri "$apiBase/documents/$($report.id)" `
    -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($saveBody))

Invoke-RestMethod -Uri "$apiBase/documents/$($report.id)"
Invoke-RestMethod -Uri "$apiBase/documents?page=1&page_size=20"
```

再次保存时使用上一次返回的 version。收到 409 时，调用方保留本地输入、读取最新详情，再决定如何合并；过期请求会整体回滚。当前 PATCH 表示一次人工保存，相同正文再次提交有效版本也会生成新版本，后续前端通过内容变更判断减少重复保存。

日报创建使用唯一索引和 INSERT ON CONFLICT，避免并发打开产生重复日报。保存把 ID、未删除条件和预期版本放在同一条 UPDATE 中，随后在同一事务中写快照；快照失败时正文与版本一起回滚。

数据库写锁超过等待时限时返回 503，响应包含 Retry-After: 1。其他数据库错误返回通用 500 信息，日志隐藏 SQL 参数。数据库结构升级通过显式命令执行，应用启动时创建连接池，关闭时释放；每个请求使用独立会话。

接口代码可以按 routes.py → schemas.py → service.py → repository.py → models.py 阅读。routes 接收参数并转换状态码，schemas 校验输入，service 控制业务事务，repository 执行查询与原子写入。HTTP 测试使用框架当前推荐的 httpx2，通过临时数据库覆盖正常流程、并发创建、版本竞争和失败回滚。

## 在 PyCharm 中运行和调试

打开项目根目录后，将解释器设为 backend/.venv/Scripts/python.exe，并将 backend 标记为 Sources Root。解释器提供第三方依赖，源码根目录帮助编辑器解析 app 包。

项目提供 .run/Backend FastAPI.run.xml 共享运行配置。在顶部运行配置列表中选择 Backend FastAPI，点击 Run 或 Debug 启动。配置使用项目选定的 Python 解释器，工作目录为 backend，当前端口为 8009。

在 main.py 上右键运行会创建针对该文件的临时配置。启动后端时，请从顶部下拉框选定 Backend FastAPI，再使用旁边的运行或调试按钮。

如果列表暂时没有出现这个配置，可以通过 Run → Edit Configurations 新建 Python 配置，填写以下内容。

| 设置 | 值 |
|---|---|
| 名称 | Backend FastAPI |
| 启动目标类型 | Module name |
| 模块名称 | uvicorn |
| 参数 | app.main:app --host 127.0.0.1 --port 8009 |
| 工作目录 | 项目根目录下的 backend |
| Python 解释器 | backend/.venv/Scripts/python.exe |

它等效于在 backend 目录执行 python -m uvicorn app.main:app --host 127.0.0.1 --port 8009。app.main 表示 app/main.py 模块，冒号后的 app 表示其中创建的 FastAPI 应用对象。

main.py 创建应用对象并注册接口，Uvicorn 根据运行配置持续监听端口并处理请求。地址和端口集中在启动配置中管理。

这份调试配置采用单进程运行，便于断点调试。修改代码后停止并重新启动即可载入更改。需要自动重载时，可以使用前面的终端启动命令。

如果启动提示 8009 端口已占用，先停止自己此前通过终端或 IDE 启动的后端，再使用这份配置运行。调整后端端口时，同时更新 frontend/vite.config.ts 中的开发代理目标。

## 启动前端

另开一个终端，进入 frontend 目录后执行以下命令。

```powershell
npm run dev
```

浏览器打开 http://127.0.0.1:5173。页面会读取日报列表；首次使用时显示空工作台。点击“写今日日报”打开今天的日报，也可以选择日期补写；同一天重复打开会读取原有内容。创建会立即保存一份初始模板，之后的编辑需要手动保存。

右侧标题可以直接修改，正文是 Markdown 原文。顶部支持编辑、分屏和预览三种视图，工具栏支持标题、加粗、斜体、列表、任务、引用、链接、代码块、表格和撤销重做。任务预览中的复选框只读，需要在原文中修改 `[ ]` 和 `[x]`。代码高亮支持 Python、JavaScript、TypeScript、JSON、Bash 和 SQL，其他语言仍显示原文。

点击“保存”或按 Ctrl+S（macOS 为 ⌘+S）提交修改，后端确认成功才显示“已保存”。标题需要 1 到 200 个字符，空正文允许保存；内容没有变化时不提交新版本。保存过程中继续输入的内容会保持待保存状态，需要再次保存。

切换日报时，未保存内容会触发“继续编辑 / 放弃修改并切换 / 保存并切换”提示，保存失败会保留草稿并阻止切换。刷新或关闭页面时浏览器会对未保存内容提示；是否展示该提示由浏览器决定。当前阶段的草稿只在页面内存中，确认离开后不会恢复。已保存日报的 ID 会写入地址栏 `?document=ID`，刷新后重新打开该日报。

遇到版本冲突时，点击“读取最新版本并比较”。“采用最新内容”会放弃当前草稿并使用服务器版本；“保留草稿，手动合并”会保留当前输入并采用最新版本号，供你比较、人工合并后再保存。这两项选择都不会自动提交内容，合并后仍可通过“查看参考版本”查看服务器内容。网络失败时保留输入，恢复后重新点击保存。

自动保存、浏览器草稿恢复、Markdown 导入导出、搜索筛选、回收站和历史版本界面留在后续阶段实现。

Vite 将 /api、/docs 和 /openapi.json 转发到本机 8009 端口，浏览器从同一个前端地址访问服务。前端端口被占用时会明确报错，避免自动切换端口造成混淆。在终端按 Ctrl+C 停止服务。

独立联调可以通过 `WORKSPACE_API_TARGET` 指向另一后端端口，例如先在终端设置 `$env:WORKSPACE_API_TARGET='http://127.0.0.1:8010'` 再运行 `npm run dev -- --port 5186`。对应后端使用独立的 `WORKSPACE_DATA_DIR` 并先执行迁移，避免将验收数据写入日常数据库。验收结束后关闭对应终端，日常启动仍使用默认 8009 和 5173。

接口文档页面的 Swagger UI 静态资源由 FastAPI 默认 CDN 提供，首次打开需要能够访问该 CDN。

## 代码检查

在 backend 目录执行以下命令。

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest -q
```

Python 格式化命令为 uv run ruff format .。Ruff 同时负责导入排序检查，Pyright 使用 basic 模式检查类型。pytest 为每个存储测试创建独立临时目录，并通过真实迁移创建表，测试数据保留在临时测试库。

在 frontend 目录执行以下命令。

```powershell
npm run lint
npm run format:check
npm run type-check
npm run test
npm run build
```

前端格式化命令为 npm run format。lint 和 format:check 检查时不会修改源码，必要时使用 npm run lint:fix 修复可自动处理的问题。npm run build 同时执行类型检查和构建，生成的 dist 目录供后续部署使用。

Vitest 使用 jsdom 模拟浏览器，回归保存失败、输入期间保存、过期请求、版本冲突、未保存切换保护以及 Markdown 清理规则；接口在测试中模拟，不连接日常数据库。编辑器采用 CodeMirror 提供选区、行号、语法着色和撤销；体积较大，打开日报时再加载。当前编辑器分包约 521 kB（gzip 约 181 kB），构建会给出超过默认 500 kB 的体积提示。

前端 package.json 通过 overrides 将检查工具的间接依赖 minimatch 固定为 11.0.1，以处理 [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249)。更新 ESLint 及相关依赖时，需要重新核对这个覆盖项并运行检查，避免跨主版本依赖出现兼容性变化。

## 从哪里阅读代码

可以按一次日报保存的顺序阅读。

1. frontend/src/main.ts 创建 Vue 应用并注册路由和 Pinia。
2. frontend/src/router/index.ts 将首页路由指向 HomeView.vue。
3. frontend/src/views/HomeView.vue 组织三栏布局、文档切换和快捷键。
4. frontend/src/components/DocumentWorkspace.vue 连接标题、编辑器、预览、保存按钮与状态。
5. frontend/src/stores/documents.ts 使用 Pinia 集中管理当前文档、草稿和保存规则。
6. frontend/src/api/documents.ts 发送请求，通过 Zod 校验响应，并统一处理失败。
7. frontend/vite.config.ts 在开发时将 API 请求转发给后端。
8. backend/app/documents/routes.py → service.py → repository.py 在事务中更新文档及快照。

编辑预览从 components/MarkdownEditor.vue → markdown/commands.ts 和 components/MarkdownPreview.vue → markdown/render.ts 阅读。前者修改 Markdown 选区；后者从原文派生 HTML，通过 DOMPurify 清理后显示。components/WorkspaceDialog.vue 使用原生 dialog 管理弹窗焦点，composables/useUnsavedChanges.ts 统一处理未保存的切换和页面离开提示。

## 目录职责

```text
frontend/        页面、接口调用、路由和前端检查配置
backend/app/    FastAPI 应用和业务模块
backend/migrations/  已发布的数据库结构迁移及生成模板
backend/tests/       配置、迁移和存储规则的自动验证
data/           本地 SQLite 数据库及后续运行数据
backend/        Python 依赖、虚拟环境和代码检查配置
AGENTS.md       初学者可维护性规范
.editorconfig   编码、换行和缩进约定
```

存储部分从 backend/app/config.py 阅读配置，再看 database.py 的连接与时间处理、documents/models.py 的表映射，最后看 migrations/versions/0001_create_documents.py 的实际建表步骤。

真实数据、环境配置和虚拟环境已经纳入 Git 忽略规则。备份功能和容器配置将在对应阶段加入。

## 当前阶段验收

1. 启动前后端，空库显示空状态；创建今日日报后，同一天重复打开不会创建重复文档。
2. 选择历史日期补写日报，在列表中切换，分页按日期倒序显示。
3. 编辑标题和 Markdown，检查标题、任务、表格、代码块预览及三种视图。
4. 点击保存和 Ctrl+S 均可保存，刷新能打开原日报并显示保存内容；重启后端后数据仍在。
5. 未保存时切换日报，继续编辑、放弃修改、保存后切换均符合选择；失败保留输入。
6. 后端关闭时保存显示失败，重启后可以重试；保存过程中继续输入的内容仍待保存。
7. 两个窗口打开同一日报，一个窗口先保存，另一窗口保存返回冲突，比较后可以明确选择保留草稿手动合并或采用最新内容。
8. 运行前端 lint、format:check、type-check、test 和 build，全部通过；数据库和后端接口继续使用前面阶段的 pytest 回归。
