# 工程规范对标参考（以 AgentScope 为范例）

本文件以一个结构工整的成熟开源项目 [AgentScope](https://github.com/modelscope/agentscope)
为例，拆解其工程规范的具体做法，作为审查时的对照基准——审查者据此判断「被审项目离这类成熟规范有多远」。
这里讲的是**可复用的做法**，不是某个项目专属的规则。

---

## 一、工程规范层

### 1.1 pre-commit 强制关卡

AgentScope 的工整不是靠人自觉，是靠机器卡关。

`.pre-commit-config.yaml` 配置了 7 个仓库串行执行：

| 阶段 | 工具 | 作用 | 关键参数 |
|------|------|------|---------|
| 基础检查 | pre-commit-hooks | 语法/格式/隐私 | check-ast、check-yaml、check-toml、check-json、detect-private-key、trailing-whitespace |
| 格式 | add-trailing-comma | 自动补尾逗号 | — |
| 类型 | mypy | 强制类型注解 | `--disallow-untyped-defs`、`--disallow-incomplete-defs` |
| 格式 | black | 代码格式化 | `--line-length=79` |
| lint | flake8 | 静态检查 | `--extend-ignore=E203` |
| lint | pylint | 深度质量检查 | 30+ 个 `--disable` 微调、复杂度上限 `--max-branches=30` |
| 打包 | pyroma | 包质量评分 | `--min=10`（必须满分） |

**核心洞察**：mypy 的 `--disallow-untyped-defs` 是关键。类型注解从"建议"变成"构建关卡"，没写注解的代码连提交都不行。

### 1.2 提交规范

- Conventional Commits 严格执行：PR 标题用 `type(scope): subject` 格式
- GitHub Actions 强制校验 PR 标题，不合规阻止合入
- AI 生成的 PR 必须原子化：禁止 10K+ 行一次性 PR

### 1.3 测试框架

- 主用 `unittest.IsolatedAsyncioTestCase`（不是 pytest fixture 风格）
- 测试按能力平铺，不是按模块镜像分层
- mock 边界清晰：只 mock 外部 SDK 客户端，被测对象的真实逻辑都执行
- 私有方法也测（模块级 `# pylint: disable=protected-access`）

---

## 二、模块组织规范

### 2.1 目录结构原则

按**能力域**分包，每个能力域是一个顶层包：

```
agentscope/
├── agent/          # 核心门面
├── model/          # 模型层
├── embedding/      # 向量
├── tool/           # 工具
├── middleware/     # 中间件
├── message/        # 消息
├── formatter/      # 格式转换
├── credential/     # 凭证
├── state/          # 状态
├── mcp/            # MCP 集成
├── pipeline/       # 流水线
├── event/          # 事件系统
├── exception/      # 异常体系
├── app/            # 服务层
├── workspace/      # 工作空间
├── _utils/         # 内部工具（_ 前缀）
├── _logging.py     # 内部日志（_ 前缀）
└── _version.py     # 内部版本（_ 前缀）
```

### 2.2 内部模块 `_` 前缀模式

**所有内部实现模块都加 `_` 前缀**：

```
model/
├── __init__.py         # 只导出公共 API
├── _base.py            # 基类（内部）
├── _model_response.py  # 响应类（内部）
├── _model_card.py      # 模型卡（内部）
├── _model_usage.py     # 用量统计（内部）
├── _utils.py           # 工具函数（内部）
├── _ollama/            # ollama provider（内部）
│   ├── __init__.py     # 导出 OllamaChatModel
│   ├── _model.py       # 实现（内部）
│   └── _models/        # 模型卡 YAML（数据，无 __init__.py）
├── _deepseek/
│   ├── __init__.py
│   └── _model.py
└── ...
```

**效果**：
- 用户从 `agentscope.model import OllamaChatModel`，干净清爽
- 内部实现细节藏在 `_` 前缀模块里，用户不会误 import
- 每个 provider 一个目录，结构对称、易找

### 2.3 `__init__.py` 三分式

每个包的 `__init__.py` 都是统一格式：

```python
"""包的一句话说明。"""

from ._base import ChatModelBase
from ._ollama import OllamaChatModel
from ._deepseek import DeepSeekChatModel
# ...

__all__ = [
    "ChatModelBase",
    "OllamaChatModel",
    "DeepSeekChatModel",
    # ...
]
```

**关键规则**：
- 第一行是 docstring
- import 都是裸名导入（用户用的时候不需要带模块前缀）
- `__all__` 与 import 一一对应
- 内部实现（`_base`、`_utils`）不导出

---

## 三、类设计规范

### 3.1 模板方法基类

基类做 80% 的公共逻辑，子类只填 20% 的差异。

以 `ChatModelBase` 为例：

| 基类承担（~741 行） | 子类承担（~350 行） |
|-------------------|-------------------|
| 重试循环 + 指数退避 | `Parameters` 嵌套类（参数定义） |
| 流式聚合（`_stream`） | `_call_api`（真正的 API 调用） |
| 结构化输出两级 fallback | `_parse_stream_response`（流式解析） |
| 工具 choice 校验 | `_parse_completion_response`（非流式解析） |
| 模型卡解析（list_models） | `_get_retryable_exceptions`（哪些异常可重试） |
| 参数校验 | `_get_disable_thinking_kwargs`（provider 差异参数） |

**子类模板**（每个 provider 都是同样的结构）：
```python
class XxxChatModel(ChatModelBase):
    class Parameters(BaseModel):
        """该 provider 的特有参数。"""
        temperature: float = 1.0
        # ...

    def __init__(self, credential, model, ...):
        # 惰性 import sdk client
        # 选 formatter
        # 调 super().__init__()

    async def _call_api(self, messages, ...):
        # 只做一件事：调 SDK、返回响应
```

### 3.2 嵌套 Parameters 类

配置 schema 和消费它的类绑定在一起：

```python
class ChatModelBase:
    class Parameters(BaseModel):
        """每个子类实现自己的参数定义。"""
```

**好处**：
- 参数和使用它的类内聚，不会散落
- 子类覆盖时用 `self.Parameters()` 作为默认值
- 配合 model card YAML 的 `parameter_class` 做类型约束

### 3.3 私有方法规范

- 所有内部方法都用 `_` 前缀
- 外部只能调用公共方法
- 基类的钩子方法（子类必须实现的）也是 `_` 前缀（如 `_call_api`）
- 子类可以调用基类的 `_` 方法（同一继承体系内合理）

---

## 四、异常体系

### 4.1 双分支异常模型

```
BaseException
├── Exception
    ├── AgentOrientedException      # 给 agent 处理的
    │   ├── ToolInterruptedError
    │   ├── ToolNotFoundError
    │   └── ...
    └── DeveloperOrientedException  # 给开发者修的
        ├── StructuredOutputError
        ├── ToolJSONDecodeError
        └── ...
```

**核心思想**：异常按"谁来处理"分层，而不是按"是什么错误"分层。

- 调用方 catch `AgentOrientedException` → 降级、重试、换策略
- 调用方 catch `DeveloperOrientedException` → 报错、日志、让开发者修

### 4.2 异常命名

- 异常类名以 `Error` 结尾
- 名字说明问题是什么，不是在哪里抛的
- 好的名字：`StructuredOutputError`、`ToolNotFoundError`
- 坏的名字：`ModelError`、`AgentError`（太泛）

---

## 五、扩展点配套清单

新增一种扩展（如一个模型 provider），必须同交付 N 件套，缺一件不合并。

### 新增模型 provider 的 5 件套

1. **Credential 类** → `agentscope/credential/`
2. **Chat model 类** → `agentscope/model/_<provider>/_model.py`
3. **Model card YAML** → `model/_<provider>/_models/*.yaml`
4. **两种 Formatter** → `agentscope/formatter/`（Chat + MultiAgent）
5. **注册** → 3 处：`model/__init__.py`、`credential/__init__.py`、`CredentialFactory._classes`

**为什么有效**：
- 不会出现"加了 model 忘了加 credential"的情况
- 不会出现"加了实现忘了注册"的情况
- 每个 provider 的完整度是一致的

---

## 六、对标差距速查（审查时填写）

审查时逐项对照，在「被审项目现状」列据实填写，再定差距等级。

| 维度 | AgentScope 标杆 | 被审项目现状 | 差距等级 |
|------|----------------|------------|---------|
| pre-commit 类型检查 | mypy `--disallow-untyped-defs` 强制 | （现场填写） | 🔴/🟠/🟡 |
| `__all__` 白名单 | 每个模块都有 | （现场填写） | 🔴/🟠/🟡 |
| 内部模块 `_` 前缀 | 几乎全部 | （现场填写） | 🔴/🟠/🟡 |
| 模板方法基类 | 基类做 80% 公共逻辑 | （现场填写） | 🔴/🟠/🟡 |
| 封装边界 | 零私有属性穿透 | （现场填写） | 🔴/🟠/🟡 |
| 异常分层 | 双分支（面向谁处理） | （现场填写） | 🔴/🟠/🟡 |
| 扩展配套清单 | 明文规定 5 件套 | （现场填写） | 🔴/🟠/🟡 |
| 猴子补丁 | 零 | （现场填写） | 🔴/🟠/🟡 |

---

## 七、落地优先级建议

**第一阶段（低成本高收益）**：
1. pre-commit 加 ruff + mypy `--disallow-untyped-defs`
2. 所有模块 `__init__.py` 补 `__all__`
3. 清除所有 `noqa: SLF001`（封装穿透）

**第二阶段（中等成本）**：
1. 对基类加强模板方法（公共逻辑上提，子类只留钩子）
2. 异常体系按"面向谁处理"分层
3. 扩展点配套清单写入 CONTRIBUTING

**第三阶段（长期方向）**：
1. 内部模块系统性加 `_` 前缀
2. 拆分上帝类（职责过重的门面类 / 路由分发层）
