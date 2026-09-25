# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目性质

这是一个**纯文档型 Claude Code Skill**，没有可运行的 Python 代码、没有构建、没有测试。所有「代码」都是 Markdown 指令集，用来指导 AI 对任意 Python 项目做质量与架构审查。改动即文档，保存即生效。

目标是开源并发布到 [skills.sh](https://skills.sh)（Vercel Labs 的 `skills` CLI 生态）。

## 目录结构（关键约定）

```
仓库根/
├── SKILL.md                        # 唯一入口：YAML frontmatter + 审查流程（即 skill 本体）
├── references/                      # 按需懒加载的清单（不要全塞进 SKILL.md）
│   ├── code-style-checklist.md
│   ├── encapsulation-checklist.md
│   ├── cohesion-coupling-checklist.md
│   ├── architecture-checklist.md
│   ├── agentscope-benchmarks.md    # AgentScope 工程规范对标
│   └── report-template.md         # 快速/深度双模式报告模板
├── README.md / install.sh / CONTRIBUTING.md / CHANGELOG.md   # 开源仓库门面
└── CLAUDE.md
```

仓库根的 `SKILL.md` 就是 skill 本体（skills.sh 标准布局，保证 `npx skills add owner/repo` 直接命中）。**不要再退回「内层同名子目录」的嵌套结构**——那是被 skills CLI 的递归兜底路径，远程/网站索引不稳定。

## Frontmatter 是硬要求，改动时务必保持

`SKILL.md` 顶部必须有完整的 `---` 围合的 YAML frontmatter，至少含 `name` 和 `description`。**历史上曾漏掉开头的 `---`  fence，导致 skills CLI 完全识别不到该 skill**（`npx skills add` 报 `missing required frontmatter field(s)`）。改 frontmatter 后一定要跑下面的校验命令。

`description` 字段同时是触发词：用户说「代码质量审查 / 全面审查 / 架构审查 / 技术债务盘点」等时靠它匹配，扩写触发场景时改这里。

## 常用命令

```bash
# 校验 skill 能否被 skills.sh CLI 正确识别（改完 SKILL.md 后必跑）
npx skills add . --list
# 期望输出："Found 1 skill" 并列出 python-quality-review；
# 若报 "No valid skills found" 或 "missing required frontmatter"，先查 --- fence。

# 本地自测：软链到用户级 skills 目录，然后在任意项目下调用
ln -sf "$(pwd)/python-quality-review" ~/.claude/skills/python-quality-review

# 发布到 skills.sh：先 push 到 GitHub 公开仓库，然后即可
#   npx skills add <github-owner>/python-quality-review
```

没有 lint / test / build 命令。

## 架构：快速模式 vs 深度模式（双模式是核心设计）

- **快速模式（默认）**：只覆盖维度 1–3（代码风格、封装边界、高内聚低耦合+游离方法），输出精简表 + P0/P1/P2。
- **深度模式**：用户说「全面/深度/完整/架构级/全项目/审计/盘点」任一关键词，或审查范围是整个项目时**自动升级**，必须覆盖全部 6 个维度（加 架构与设计模式、测试质量、依赖与配置）并附改进路线图。
- 问题统一按 **P0/P1/P2/P3** 分级，位置必须可定位到 `文件路径:行号`，修复建议要给代码片段。

新增/修改维度时，三处必须同步：`SKILL.md` 的六步流程图与维度表、`references/` 下对应清单、`report-template.md`。

## 写作与隐私约定

- 所有文档用中文；清单写法遵循 `CONTRIBUTING.md`：检查方法 → 红线/黄线 → 好例子/坏例子 → 可量化的合格标准。
- **示例代码一律用通用占位名**（`AgentApp`、`_from_client`、`your_package`）。历史上示例里曾混入过真实内部项目/产品代号，已全部清除——提交前自查不要把任何内部仓库名、产品名、路径写回公开文档。
- 提交信息前缀：`feat:` / `fix:` / `docs:` / `refactor:`。
