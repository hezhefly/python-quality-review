# 代码风格检查清单

对标 AgentScope 工程规范 + python-refactoring 坏味道体系。

## 1. 类型注解

### 检查方法
grep 没有类型注解的函数定义（用 AST 或人工抽查）。

### 红线
- ❌ 公共方法缺少参数或返回值类型注解
- ❌ 用 `# type: ignore` 逃避类型检查且无注释说明
- ❌ `Any` 滥用（能用具体类型就不要用 Any）

### 合格标准
- 公共方法 100% 有完整类型注解（参数 + 返回值）
- 私有方法注解覆盖率 ≥ 80%
- `Any` 必须有注释说明为什么只能用 Any

### AgentScope 做法
- pre-commit 强制 mypy `--disallow-untyped-defs --disallow-incomplete-defs`
- 类型注解是构建关卡，不是风格建议

## 2. 命名规范

### 检查项
| 元素 | 规范 | 反例 |
|------|------|------|
| 类名 | PascalCase 大驼峰 | `my_class`、`myClass` |
| 函数/方法 | snake_case 小写下划线 | `MyFunction`、`myFunc` |
| 常量 | UPPER_SNAKE_CASE | `max_retries`（函数内的常量可放宽） |
| 私有成员 | `_` 单下划线前缀 | 直接暴露内部状态 |
| 内部模块 | `_` 单下划线前缀 | 实现细节模块无前缀 |
| 异常类 | 大驼峰 + `Error` 后缀 | `my_exception`、`MyWarn` |

### 命名质量信号
- 好名字：读名字就知道做什么，不需要看注释
- 坏名字：`util`、`helper`、`manager`、`handler`（太泛）
- 坏味道：`_tmp`、`_temp`、`xxx2`（说明没想清楚职责）

## 3. Docstring

### 要求
- 公共类 / 公共方法 / 公共函数必须有 docstring
- 格式：Google 风格
- 内容：简要说明 + Args + Returns + Raises（如适用）

### 检查项
- ❌ 公共 API 无 docstring
- ❌ docstring 只说"做什么"，不说参数和返回值
- ⚠️ 私有方法 docstring 风格不统一（有的完整有的只有一句话）

## 4. 函数/方法长度

### 阈值
| 类型 | 理想 | 警告 | 必须重构 |
|------|------|------|---------|
| 函数/方法 | ≤ 30 行 | 50 行 | 80 行 |
| 类 | ≤ 300 行 | 500 行 | 1000 行 |
| 模块 | ≤ 300 行 | 500 行 | 1000 行 |

### 注
- docstring 和空行不计入
- 超过阈值不一定是坏事（如 AgentScope 的 `Agent` 类 3900 行是架构取舍），但必须有正当理由

## 5. 异常处理

### 红线
- ❌ 裸 `except:`（必须捕获具体异常类型）
- ❌ `except Exception:` 之后静默吞掉（不记录日志就 pass）
- ❌ `raise RuntimeError("...")`（应该用自定义异常 + 错误码）

### 合格做法
```python
# ✅ 正确：捕获具体异常 + loguru 记录 + 抛自定义异常
try:
    result = self._graph.invoke(state, config=config)
except ValueError as exc:
    logger.error(f"图执行失败: {exc}")
    raise GraphExecutionError(f"执行失败: {exc}") from exc
```

### AgentScope 做法
异常按"面向谁处理"分层：
- `AgentOrientedException` — agent 运行时可自行处理
- `DeveloperOrientedException` — 开发者要修的 bug

## 6. 导入规范

### 导入顺序
1. 标准库
2. 第三方库
3. 本地项目库

每组之间空一行。

### 红线
- ❌ 通配符导入（`from xxx import *`）
- ❌ 循环导入
- ❌ 函数内部 import 替代顶层导入（惰性导入除外，需注释说明）

### 惰性导入
可选依赖（如 redis、pandas）用惰性导入，在函数内部 import，ImportError 时给出清晰的安装提示。
