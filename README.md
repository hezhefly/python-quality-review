# python-quality-review

**English**: [README_EN.md](README_EN.md)

> 面向 Python 项目的代码质量与架构审查 **Claude Code Skill**。
> 从 **代码风格 / 封装边界 / 高内聚低耦合 / 游离方法 / 架构设计 / 测试质量**
> 六大维度做系统性审查，输出按 P0–P3 分级的结构化质量报告。
> 审查标准综合自成熟开源项目的工程实践与经典代码坏味道（code smell）体系。

## 它解决什么问题

通用 `code-review` 技能关注「这段代码能不能跑 / 有没有 bug」，
但对 **架构是否站得住** 几乎不说话。
本技能专门回答另一个问题：

> 这个 Python 项目的**工程质量**到没到开源标准？

典型场景：

- 接手一个陌生 Python 仓库，想快速知道哪里有技术债
- PR 合并前做一次架构级别的扫描
- 准备开源前对齐主流开源项目的工程规范
- 给团队出一份能进周报/述职的「质量基线报告」

## 审查的六个维度

| 维度               | 审查重点                     | 关键检查项                             |
| ---------------- | ------------------------ | --------------------------------- |
| 1. 代码风格          | 坏味道识别体系                  | 类型注解覆盖率、命名、docstring、行宽、异常处理、导入顺序 |
| 2. 封装边界          | 公共/内部边界                  | `_` 前缀穿透、`__all__`、猴子补丁、动态挂载      |
| 3. 高内聚低耦合 + 游离方法 | 高内聚 / LCOM               | 游离函数、假类、utils 滥用、跨模块直操内部状态        |
| 4. 架构与设计模式       | 模板方法 / 注册表 / 分层           | 基类设计、扩展点配套、if-elif 分发链、异常体系分层     |
| 5. 测试质量          | 真实性原则                    | mock 一切、flaky sleep 轮询、核心模块无单测    |
| 6. 依赖与配置         | 可选依赖 / 集中配置               | 可选依赖分组、惰性导入、配置集中管理                |

详细检查清单见 [`references/`](references/)。

## 两种工作模式

| <br /> | 快速模式（默认）                | 深度模式                  |
| ------ | ----------------------- | --------------------- |
| 触发     | 「看下这个模块」「review 一下这个文件」 | 「全面审查」「深度审计」「全项目质量盘点」 |
| 覆盖     | 维度 1–3                  | 全部 6 个维度              |
| 输出     | 精简表格 + P0/P1/P2 问题清单    | 完整六维报告 + 改进路线图        |
| 适用     | 单文件 / 单模块               | 全项目 / 正式报告 / 开源前盘点    |

只要用户说「全面 / 深度 / 完整 / 架构级 / 全项目 / 审计 / 盘点」任一关键词，自动升级为深度模式。

## 安装

### 方式一：skills.sh CLI（推荐，支持所有 coding agent）

```bash
# 全局安装到 Claude Code
npx skills add hezhefly/python-quality-review -g -a claude-code -y

# 或同时装到多个 agent（Codex / Cursor / OpenCode 等）
npx skills add hezhefly/python-quality-review -g -a claude-code -a cursor -y
```

### 方式二：Claude Code 手动复制（用户级）

```bash
git clone https://github.com/hezhefly/python-quality-review.git
cd python-quality-review
mkdir -p ~/.claude/skills/python-quality-review
cp SKILL.md ~/.claude/skills/python-quality-review/
cp -R references ~/.claude/skills/python-quality-review/
```

重启 Claude Code 后即可通过 `python-quality-review` 名称调用。

### 方式三：一键脚本

```bash
curl -fsSL https://raw.githubusercontent.com/hezhefly/python-quality-review/main/install.sh | bash
```

脚本不带参数装到用户级 `~/.claude/skills/`；传项目路径则装到该项目的 `.claude/skills/`。

## 使用

在 Claude Code 里直接说：

```
对当前项目做一次全面质量审查
```

或：

```
python-quality-review: review 一下 src/your_package/agent/ 这个模块
```

技能会自动判断是快速模式还是深度模式，输出 Markdown 报告到当前会话，
报告模板见 [`references/report-template.md`](references/report-template.md)。

## 最佳实践：怎么用效果最好

### 1. 先跑预检脚本，再让 AI 深读

脚本摆客观事实，AI 判语义。把两者串起来：

```bash
# 第一步：机器先扫，拿到 P0/P1 客观清单
python scripts/preflight.py src/ --min-severity P1
```

然后把结果喂给 Claude Code：

```
把 preflight 的输出过一遍：确认真正该修的（排除误报），
对每个 P0/P1 给出具体修复代码片段，再补人工维度（游离方法、测试真实性）。
```

这样 AI 不会在「哪里有问题」上浪费时间，直接聚焦「为什么、怎么改」。

### 2. 按场景选对触发语

| 你想要的 | 这么说 |
|---------|--------|
| 快速看一个文件/模块 | 「快速 review 一下 `src/foo/bar.py`」 |
| 全项目正式报告 | 「对当前项目做一次**全面**质量审查」 |
| 开源前对齐规范 | 「**深度审计**，按 P0–P3 出改进路线图」 |
| 接手陌生仓库 | 「**全项目盘点**，先给技术债总览」 |
| 只看某一维 | 「只查**封装边界**：有没有跨模块访问 `_private`」 |

### 3. 别让它一次改太多

本技能**只出报告 + 路线图，不直接动手改**。拿到 P0 清单后：

- 一次只让它修 P0（2–5 个），每修完一类再要下一类
- 大修（拆上帝类、改异常体系）先让它出**方案对比**，确认后再改
- 改完用 `python scripts/preflight.py .` 回归，看 P0/P1 是否清零

### 4. 和其他技能串成流水线

```
本技能（找问题） → python-refactoring（动手修） → code-review（验证没改坏）
```

### 5. 把报告留下来当基线

- 深度报告存成 `docs/quality-baseline-YYYY-MM.md`，下个季度对比，看 P0 是否下降
- 接 CI：`python scripts/preflight.py . --min-severity P1` 退出码非零即拦截，防技术债新增

## 与其他技能的关系

- **python-refactoring**：侧重「动手改代码」。本技能侧重「找问题 + 出报告 + 路线图」。两者串起来用：先本技能审查 → 再 python-refactoring 修复。
- **code-review**：通用功能 / bug 审查。本技能是架构与工程化维度的补充。
- **security-audit**：安全是独立维度，本技能只在封装边界顺带覆盖。
- **simplify**：侧重代码精简。本技能是系统性全维度。

## 仓库结构

```
.
├── SKILL.md                   # 技能主入口（frontmatter + 流程）
├── references/                # 检查清单 / 报告模板
│   ├── code-style-checklist.md
│   ├── encapsulation-checklist.md
│   ├── cohesion-coupling-checklist.md
│   ├── architecture-checklist.md
│   ├── best-practices-benchmarks.md
│   └── report-template.md
├── scripts/                   # 零依赖预检脚本（纯 ast，无需 pip install）
│   ├── preflight.py           #   自动锁定 P0/P1 客观问题
│   └── README.md
├── install.sh                 # 一键安装脚本
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

> 仓库根的 `SKILL.md` 即 skill 本体——这是 skills.sh / skills CLI 的标准布局，
> 保证 `npx skills add hezhefly/python-quality-review` 能直接命中。

## 路线图

- [x] 预检脚本支持 JSON 输出（preflight.py `--json`，可接 CI）
- [ ] 增加 ruff / mypy / pylint 结果的自动化预扫
- [ ] 新增 FastAPI / LangGraph / Pydantic 项目专属配置档
- [ ] 提供 `examples/` 真实项目审查样本

## License

[MIT](LICENSE)
