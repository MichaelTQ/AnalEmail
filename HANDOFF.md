# 项目交接记录（Handoff）

> 面向学生开发者的维护笔记。每次对项目做实质修改后，应同步更新本文档。

## 1. 当前状态

- 最后更新：2026-07-18
- 当前阶段：第一阶段——验证环境并只读获取最近 10 封 163 邮件
- 代码状态：已完成
- 离线测试：已通过
- 真实邮箱测试：已定位并修复 163 `Unsafe Login`，只读获取最近 10 封邮件已通过
- 当前明确不包含：AI 分析、数据库、网页界面、Docker、AnythingLLM、自动回复或发送

项目路径：

```text
/Users/michael/Desktop/AnalEmail/AnalEmail
```

## 2. 本次完成了什么

创建了以下文件：

```text
AnalEmail/
├── main.py
├── email_client.py
├── email_parser.py
├── config.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── HANDOFF.md
```

实现内容：

1. 从项目目录的 `.env` 加载邮箱配置。
2. 校验必需配置，并把端口和读取数量转换为整数。
3. 使用 `imap-tools` 通过 SSL 连接 163 IMAP 服务。
4. 显式以只读模式打开 `INBOX`。
5. 登录后发送真实的 IMAP 客户端 `ID`，满足 163 的连接检查。
6. 获取最近最多 10 封邮件，并按邮件时间从新到旧排列。
7. 使用标准库 `email` 解析邮件结构和 MIME 标题。
8. 支持 UTF-8、GB18030、GBK、Big5 等常见编码回退。
9. multipart 邮件优先提取 `text/plain`；没有纯文本时清理 `text/html`。
10. 识别附件，并避免把附件内容当作正文。
11. 终端显示 UID、发件人、标题、时间、附件状态和正文前 500 个字符。
12. 单封邮件解析失败时继续处理后续邮件，最后统计成功和失败数量。

## 3. 程序调用链

运行：

```bash
python main.py
```

主要调用顺序：

```text
main.py
  ├── config.load_config()
  │     └── 读取并校验 .env
  ├── email_client.fetch_recent_emails()
  │     ├── SSL 连接 163
  │     ├── 使用授权码登录
  │     ├── 发送 IMAP 客户端 ID
  │     ├── 只读打开 INBOX
  │     ├── 获取邮件
  │     └── finally 中退出连接
  └── 对每封邮件调用 email_parser.parse_email()
        ├── 解码标题和发件人
        ├── 解析日期
        ├── 提取纯文本或 HTML 正文
        └── 检查附件
```

理解这条调用链后，再逐个阅读文件会更容易。

## 4. 各文件职责

### `config.py`

- `Config`：不可变配置数据类。
- `ConfigError`：可直接向用户展示的配置错误。
- `load_config()`：从项目目录读取 `.env`，因此不依赖启动时的当前目录。
- `_read_positive_int()`：集中处理整数转换和正数校验。

安全原则：配置错误中只显示变量名，不显示授权码内容。

### `email_client.py`

- `fetch_recent_emails()`：负责连接、登录、选取目录、读取和退出。
- `EmailClientError`：把底层网络或 IMAP 异常转换成清晰的中文信息。
- `_sort_date()`：将邮件日期统一成可比较的 UTC 时间；异常日期排在最后。

关键只读设置：

```python
mailbox.login(..., initial_folder=None)
_send_client_id(mailbox)
mailbox.folder.set("INBOX", readonly=True)
mailbox.fetch(..., mark_seen=False)
```

这里先阻止 `login()` 自动选取目录，发送 163 所需的客户端 `ID`，再显式使用只读方式打开 `INBOX`。`mark_seen=False` 避免读取正文时添加已读标记。客户端 ID 只包含项目名、版本和本地项目类型，不包含邮箱地址或授权码。

### `email_parser.py`

- `decode_mime_header()`：解码 MIME 标题。
- `_decode_bytes()`：按声明编码、UTF-8、GB18030、GBK、Big5、Latin-1 依次尝试。
- `extract_body()`：优先纯文本，必要时将 HTML 转成纯文本。
- `_is_attachment()`：通过 Content-Disposition 或文件名识别附件部分。
- `parse_email()`：返回统一字典。

返回结构：

```python
{
    "uid": "12345",
    "sender": "example@example.com",
    "subject": "邮件标题",
    "date": "2026-07-18 15:30:00",
    "body": "完整正文",
    "has_attachment": False,
}
```

解析函数保留完整正文，只有 `main.py` 在展示时截取前 500 个字符。

### `main.py`

- 组织整个程序流程。
- 顶层配置或连接错误返回退出码 `1`。
- 单封邮件失败不会中断循环。
- 全部解析成功返回 `0`；存在单封解析失败时返回 `2`。

### 其他文件

- `requirements.txt`：只包含 `imap-tools`、`beautifulsoup4`、`python-dotenv`。
- `.env.example`：安全配置模板，不得写入真实授权码。
- `.gitignore`：确保 `.env`、虚拟环境和 Python 缓存不进入 Git。
- `README.md`：面向使用者的安装、配置、运行、验收和故障排查说明。
- `HANDOFF.md`：面向维护者的实现说明和开发记录。

## 5. 关键设计取舍

### 为什么使用授权码

163 的第三方客户端登录使用客户端授权码。邮箱网页登录密码不应写入项目，也不应作为 IMAP 凭据使用。

### 为什么优先 `text/plain`

同一封 multipart 邮件常同时包含纯文本和 HTML 两份相同内容。如果两者都拼接，正文会重复。因此有纯文本时只使用纯文本，没有时才清理 HTML。

### 为什么带文件名的 MIME 部分也视为附件

有些邮件没有正确设置 `Content-Disposition: attachment`，但设置了文件名。把这类部分排除可以降低二进制附件被误解码成正文的风险。

### 为什么不向用户显示原始异常详情

底层认证异常可能包含服务器返回信息。对用户输出经过整理的中文错误，更容易理解，也减少意外泄露敏感信息的可能。

### “最近 10 封”的含义

客户端先以 IMAP 倒序取得收件箱中最近到达的最多 10 封，再根据这些邮件的 `Date` 头排序。损坏或缺失日期的邮件排在最后。

## 6. 已完成的验证

使用项目虚拟环境进行了以下检查：

- Python 文件 AST 语法检查：通过。
- 四个项目模块实际导入：通过。
- `pip check` 依赖一致性检查：通过。
- `.env.example` 加载及整数转换：通过。
- UTF-8 中文和英文混合标题、正文：通过。
- GBK MIME 标题、发件人和正文：通过。
- multipart 纯文本优先：通过。
- HTML 转纯文本并移除 `script`、`style`：通过。
- 附件检测及附件正文排除：通过。
- 发件人为空的回退显示：通过。
- 连续空行合并：通过。
- 模拟 IMAP 行为检查：只读 `INBOX`、`mark_seen=False`、数量限制、倒序获取、正确退出均通过。
- 缺少 `.env` 时的中文错误：通过。

真实环境最新结果：

- 开发者已经在 163 网页端开启 IMAP/SMTP，并生成授权码写入 `.env`。
- 初次运行收到“IMAP 操作失败”。脱敏诊断确认底层异常为 `MailboxFolderSelectError`，服务器响应为 `EXAMINE Unsafe Login`。
- 163 网页端随后显示“授权码可能泄漏”的安全风险提示。
- 根因是 163 接受了授权码登录，但拒绝没有客户端 ID 的 `EXAMINE INBOX`。
- 在登录后发送真实、非敏感的 IMAP `ID` 后，服务器返回 `OK`，只读打开 `INBOX` 并获取 10 封邮件成功。
- 修复已加入正式代码；不得在聊天、日志或 Handoff 中记录授权码。

尚未验证：

- 真实收件箱中 10 封不同来源邮件的显示结果。
- 运行前后真实未读邮件状态是否保持不变。

这些项目需要开发者提供自己的邮箱配置，不能用示例凭据完成。

## 7. 当前本地环境

- 系统默认 `/usr/bin/python3`：Python 3.9.6，不满足要求。
- pyenv 已安装：Python 3.12.2。
- 项目 `.venv`：已使用 Python 3.12.2 创建。
- 项目依赖：已安装到 `.venv`。
- `.env`：已由开发者创建并配置，内容不得记录或提交；忽略规则已验证生效。

Git 状态：

- 正确仓库根目录：`/Users/michael/Desktop/AnalEmail/AnalEmail`
- 远程：`origin` → `https://github.com/MichaelTQ/AnalEmail.git`
- 当前分支：`main`
- 已保留原有初始提交 `1ba4f08`。
- `.env`、`.venv/` 和 `__pycache__/` 已确认被忽略。
- 项目代码目前尚未提交，显示为未跟踪文件；是否提交和推送由开发者决定。

现有虚拟环境可直接使用：

```bash
cd /Users/michael/Desktop/AnalEmail/AnalEmail
source .venv/bin/activate
python --version
```

预期版本为 `Python 3.12.2`。

如需从零重建，应先让 pyenv 使用 3.12.2：

```bash
pyenv local 3.12.2
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 8. 开发者下一步操作

按顺序执行：

```bash
cd /Users/michael/Desktop/AnalEmail/AnalEmail
source .venv/bin/activate
cp .env.example .env
```

编辑 `.env`，填入真实邮箱地址和客户端授权码，然后运行：

```bash
python main.py
```

验收重点：

1. 终端能显示最近最多 10 封邮件。
2. 中英文标题、发件人和正文可读。
3. HTML 邮件中没有明显 HTML 标签。
4. 附件没有混入正文。
5. 运行后未读邮件仍保持未读。
6. 最后一行成功数量符合实际显示数量。
7. `.env` 未被 Git 跟踪。

可以检查忽略状态：

```bash
git status --ignored
```

## 9. 常见维护风险

- 不要在代码、测试、截图或提交信息中粘贴真实授权码。
- 不要把 `readonly=True` 或 `mark_seen=False` 删除，除非需求明确改变。
- 不要在解析阶段直接截断正文；未来摘要功能可能需要完整文本。
- 不要捕获异常后完全静默；至少保留 UID 和安全的错误类型，方便定位坏邮件。
- 不要为了解析正文而遍历附件内容。
- 不要把当前阶段扩展成发送邮件或自动回复功能。
- 修改依赖版本后应重新执行导入测试和 `python -m pip check`。

## 10. Handoff 更新规则

以后每次修改项目，应至少更新以下内容：

1. 修改日期和当前阶段状态。
2. “本次完成了什么”。
3. 新增或修改的文件职责。
4. 重要设计决定以及为什么这样做。
5. 实际运行过的测试及结果。
6. 尚未验证的问题和已知限制。
7. 下一位开发者应执行的具体步骤。

推荐在文档顶部持续维护状态，在底部追加简短变更记录。

## 11. 变更记录

### 2026-07-18

- 从零创建第一阶段项目结构。
- 完成配置、只读 IMAP 客户端、邮件解析和终端输出。
- 修正 `imap-tools 1.13.0` 的异常基类为 `ImapToolsError`。
- 修正中文发件人姓名被重新显示为 MIME 编码串的问题。
- 使用 Python 3.12.2 重建 `.venv` 并安装依赖。
- 完成离线解析、模块导入、配置和只读 IMAP 行为测试。
- 新增本交接文档。
- 记录第一次真实邮箱测试：IMAP/SMTP 已开启，但登录后的 IMAP 操作被服务器拒绝，网页端出现授权码风险提示；未记录任何敏感配置。
- 脱敏诊断确认服务器拒绝原因为 `EXAMINE Unsafe Login`。
- 验证登录后发送 IMAP 客户端 `ID` 可解决问题，并成功只读获取 10 封邮件。
- 将客户端 ID 逻辑及针对 `Unsafe Login` 的明确错误提示加入正式代码。
- 记录 `git check-ignore` 失败仅因目录尚未初始化为 Git 仓库，与 IMAP 无关。
- 修复 Git 根目录：将 `.git` 和已提交的 `.gitattributes` 从错误的嵌套目录 `AnalEmal/AnalEmail` 迁移到真实项目目录 `AnalEmal/email-ai-assistant`。
- 验证 `origin`、`main` 和初始提交历史均保留，敏感 `.env` 与虚拟环境继续被正确忽略。
- 删除空的错误嵌套目录，将外层 `AnalEmal` 更名为 `AnalEmail`，并将实际 Git 根目录 `email-ai-assistant` 更名为 `AnalEmail`；最终仓库路径为 `/Users/michael/Desktop/AnalEmail/AnalEmail`。
