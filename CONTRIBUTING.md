# 贡献指南

感谢你想为 `python-quality-review` 出力。

## 这个项目是什么

它不是 Python 代码库，而是一份 **Claude Code Skill**（Markdown 指令集）。
贡献主要是：

- 扩充 / 修订 `references/` 下的检查清单
- 改进 `SKILL.md` 的触发词、流程描述、模式判定
- 提供真实项目的审查样本（放到 `examples/`）
- 改进报告模板

## 本地开发

Skill 本身不需要编译，但可以这样本地自测：

```bash
# 链接到 Claude Code 用户目录（仓库根就是 skill 本体）
ln -sf "$(pwd)" ~/.claude/skills/python-quality-review

# 然后在任意项目下启动 Claude Code，说「python-quality-review: review 一下 xx 模块」
```

修改后立刻生效，无需重启 Claude Code（如果没生效，重启一次）。

## 提交规范

- `feat:` 新增检查维度 / 清单
- `fix:` 修正错误判定标准
- `docs:` 文档改进
- `refactor:` 重组 SKILL.md 结构

## 清单写法约定

每个 checklist 文件应包含：

1. **检查方法**：怎么定位这类问题（grep 模式 / AST / 人工读）
2. **红线 / 黄线**：零容忍问题 vs 需关注问题
3. **好的例子**：对照成熟开源项目与标准库
4. **坏的例子**：典型反模式代码片段
5. **合格标准**：能量化就量化（覆盖率 / 行数 / 阈值）

## 报告模板约定

- 快速模式只输出 P0 / P1 / P2，不展开
- 深度模式必须输出六个维度 + 改进路线图
- 问题位置必须可定位到文件路径 + 行号
- 修复建议要给代码片段，不要只给抽象方向
