# scripts/ — 零依赖预检工具链

在人工深读代码**之前**先跑这些脚本，客观、快速地锁定值得做质量提升的点。
全部只用 Python 标准库（`ast`），**无需 pip install**，拷到任何 Python 仓库即可运行。

## preflight.py

聚合扫描器，一个脚本覆盖六大维度中可静态判定的部分：

| 检查项 | 对应维度 | 级别 |
|--------|---------|------|
| 猴子补丁（`Class.method = func` 模块级挂载） | 封装边界 | P0 |
| 裸 `except:` | 代码风格 | P0 |
| 跨对象访问 `obj._private` | 封装边界 | P1 |
| 跨模块 `from B import _internal` | 封装/耦合 | P1 |
| 上帝类（≥1000 行） | 高内聚低耦合 | P1 |
| 假类（全 staticmethod、无实例状态） | 高内聚低耦合 | P2 |
| 超长函数（≥80 行） | 代码风格 | P2 |
| if-elif 类型分发链（≥5 分支） | 架构设计 | P2 |
| 模块公共 API 过多（≥7 个顶层定义） | 高内聚低耦合 | P2 |
| 过宽 `except Exception` | 代码风格 | P2 |

### 用法

```bash
# 表格输出（人看）
python scripts/preflight.py /path/to/project

# JSON 输出（接 CI / 看板）
python scripts/preflight.py /path/to/project --json

# 只看 P0/P1（快速定位最该动手的点）
python scripts/preflight.py /path/to/project --min-severity P1
```

退出码：发现 P0/P1 时为 `1`，否则为 `0`——可直接挂 CI 门禁。

### 它**不**做什么（仍需人工）

- 游离方法的语义判断（「这函数该不该属于那个类」需读逻辑）
- 模板方法基类是否设计合理
- 测试真实性（是否 mock 一切）
- 抽象分层、异常语义是否恰当

这些由 SKILL.md 的六步流程人工完成；preflight 只负责把客观问题先摆到桌面上。

## 外部 CLI（可选增强）

preflight 没覆盖、但生态现成的工具——装了就能用，没装跳过：

| 工具 | 补什么 | 安装 |
|------|--------|------|
| `ruff`（含 SLF001 规则） | 私有属性穿透、风格、未用导入 | `pip install ruff` |
| `radon` | 圈复杂度、可维护性指数 | `pip install radon` |
| `grimp` / `import-linter` | 模块依赖图、循环依赖、分层违规 | `pip install grimp import-linter` |
| `deptry` | 装了没用 / 用了没装的依赖 | `pip install deptry` |
| `coverage.py` / `mutmut` | 测试覆盖盲区、变异测试 | `pip install coverage mutmut` |
