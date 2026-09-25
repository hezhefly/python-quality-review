# 架构与设计模式审查清单

参照成熟开源项目的架构模式，检查 Python 项目的架构设计质量。

## 1. 基类设计质量

### 好的基类（AgentScope 风格）

**特征一：模板方法模式**
基类定义流程骨架，子类只实现差异化钩子。

```python
# ✅ AgentScope ChatModelBase.__call__ 风格
class ChatModelBase:
    async def __call__(self, messages, tools=None, **kwargs):
        """执行完整调用：重试 + 流式/非流式 + 结构化输出兜底。"""
        retryable = self._get_retryable_exceptions()
        for attempt in range(self.max_retries + 1):
            try:
                res = await self._call_api(messages, tools=tools, **kwargs)
                return res
            except retryable as exc:
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))

    @abstractmethod
    async def _call_api(self, messages, tools, **kwargs):
        """子类实现：真正的 API 调用。"""
        ...
```

**特征二：嵌套 Parameters 类**
配置 schema 和消费它的类内聚在一起。

```python
class ChatModelBase:
    class Parameters(BaseModel):
        """每个子类实现自己的参数定义。"""

    parameters: Parameters
```

**特征三：契约完整**
基类声明了所有子类必须实现的抽象方法和属性。外部只依赖基类接口，不依赖具体子类。

### 检查项

| 检查项 | 标准 |
|--------|------|
| 基类有模板方法 | 公共逻辑在基类，差异在子类钩子 |
| 抽象方法完整 | 子类必须实现的都声明为 abstract |
| 子类只做差异化 | 每个子类只实现基类预留的钩子 |
| 外部依赖基类 | 调用方用基类类型，不用具体子类 |

### 坏味道

- ❌ 基类是空壳，所有逻辑都在子类重复
- ❌ 每个子类有几百行相同/相似的代码
- ❌ 新增一个子类需要复制粘贴大量代码
- ❌ 子类直接访问基类的私有属性

---

## 2. 扩展点质量

### 好的扩展点（AgentScope 风格）

**特征一：配套清单明确**
新增一种扩展（如一个模型 provider）必须同交付 N 件套，缺一件不合并。

```
新增模型 provider 的 5 件套：
1. Credential 类
2. Chat model 类
3. Model card YAML
4. 两种 Formatter（Chat + MultiAgent）
5. 三处注册（model/__init__.py + credential/__init__.py + Factory）
```

**特征二：显式注册，不靠自动扫描**
工厂/注册表有显式的注册列表，不用模块扫描、不用 import 魔法。

```python
# ✅ 显式注册，一目了然
class CredentialFactory:
    _classes: list[Type[CredentialBase]] = [
        AnthropicCredential,
        OpenAICredential,
        DashScopeCredential,
        # ...
    ]
```

**特征三：Pydantic discriminated union 做工厂**
用 `Union[TypeA, TypeB, ...]` + `Field(discriminator="type")` 实现类型驱动的反序列化。

### 检查项

| 检查项 | 标准 |
|--------|------|
| 扩展有配套清单 | 新增一种扩展需要做什么，写得明明白白 |
| 注册方式显式 | 有集中的注册表/工厂，不用自动扫描 |
| 扩展点数量可控 | 扩展点 ≤ 7 个，每个扩展点职责清晰 |
| 新增扩展成本低 | 新增一种扩展只需要改 N 个固定位置 |

### 坏味道

- ❌ 新增一种扩展要改 N 个散落在各处的地方（散弹式修改）
- ❌ 注册表靠 `__init__.py` 里的 side-effect 自动注册
- ❌ 没有文档说明"如何新增一种 Xxx"
- ❌ if-elif 链做类型分发，每加一种类型要加长链

---

## 3. 工厂模式 vs if-elif 链

### 什么时候该用工厂/注册表

if-elif 超过 5 个分支，且每个分支都是"根据类型创建/分发" → 用注册表模式。

```python
# ❌ if-elif 长链
def translate(event: dict) -> Generator:
    etype = event.get("type")
    if etype == "TEXT_BLOCK_START":
        yield from _on_text_start(event)
    elif etype == "TEXT_BLOCK_DELTA":
        yield from _on_text_delta(event)
    elif etype == "TEXT_BLOCK_END":
        yield from _on_text_end(event)
    # ... 16 个分支

# ✅ 注册表模式
_EVENT_HANDLERS: dict[str, Callable[[dict], Generator]] = {
    "TEXT_BLOCK_START": _on_text_start,
    "TEXT_BLOCK_DELTA": _on_text_delta,
    "TEXT_BLOCK_END": _on_text_end,
    # ...
}

def translate(event: dict) -> Generator:
    handler = _EVENT_HANDLERS.get(event.get("type"))
    if handler:
        yield from handler(event)
```

### 检查方法
grep `elif.*==` 找长链，数分支数。超过 5 个且是类型分发 → 建议重构。

---

## 4. 异常体系设计

### AgentScope 的双分支异常模型

```python
class AgentOrientedException(Exception):
    """期望被 agent 捕获并处理的异常。
    agent 收到这个异常时，可以尝试自行恢复（重试、换工具、问用户）。
    """

class DeveloperOrientedException(Exception):
    """抛给开发者的异常。
    说明代码有 bug 或配置错误，需要开发者修复。
    """
```

**为什么好**：
- 调用方一眼就知道该怎么处理这个异常
- catch 的粒度清晰：catch AgentOriented 做降级，catch DeveloperOriented 直接报错
- 异常的语义和它的名字一致

### 检查项

| 检查项 | 标准 |
|--------|------|
| 异常分层清晰 | 按"面向谁处理"分大类 |
| 自定义异常体系 | 所有业务异常继承自定义基类 |
| 错误码统一管理 | 错误码在枚举中集中定义 |
| 不用通用异常 | 没有裸 `raise RuntimeError` / `raise Exception` |

### 坏味道

- ❌ 所有异常都继承一个 `BaseError`，不区分类型
- ❌ 到处 `raise RuntimeError("xxx")`
- ❌ 错误码散落在各处字符串里，没有集中管理
- ❌ catch 全是 `except Exception`，不分异常类型

---

## 5. 中间件/插件模式

### 好的插件系统（AgentScope 风格）

- 插件基类有明确的钩子方法（可选覆盖，不是全部必须实现）
- 核心运行时探测插件实现了哪些钩子，预分类后按序调用
- 插件可以在 before/after 两个时机插入，形成洋葱模型

```python
# ✅ AgentScope MiddlewareBase 风格
class MiddlewareBase:
    def on_reply(self, *args, **kwargs): ...  # 可选实现
    def on_reasoning(self, *args, **kwargs): ...  # 可选实现
    def on_model_call(self, *args, **kwargs): ...  # 可选实现
    # ... 共 7 个钩子
```

核心运行时在 `__init__` 里预分类：
```python
self._reply_middlewares = [m for m in middlewares if hasattr(m, "on_reply")]
```

### 检查项

- ✅ 插件基类有明确的钩子定义
- ✅ 新增插件只需要继承基类、实现需要的钩子
- ✅ 插件执行顺序可控
- ❌ 插件接口太复杂，每个插件必须实现 10+ 个方法
- ❌ 插件可以直接改核心运行时的内部状态

---

## 6. 依赖管理

### 好的依赖组织（AgentScope 风格）

**超细粒度 optional-dependencies**：每个可选能力一个 extra，最后聚合为 full。

```toml
[project.optional-dependencies]
model-gemini = ["google-genai"]
model-ollama = ["ollama>=0.5.4"]
storage-redis = ["redis"]
storage-sql = ["sqlalchemy[asyncio]>=2.0", "alembic>=1.13"]
workspace-docker = ["aiodocker"]
# ... 20+ 个 extra
full = [
    "agentscope[models]",
    "agentscope[service]",
    "agentscope[storage-redis]",
    # ...
]
```

**配合惰性导入**：可选依赖只在用到时才 import，ImportError 给出清晰的安装提示。

### 检查项

- ✅ 可选依赖用 extras 分组，不用不装
- ✅ 可选依赖的代码用惰性导入，不在顶层 import
- ✅ ImportError 消息清晰，告诉用户装什么
- ❌ 所有依赖都在 requirements.txt 里一古脑全装
- ❌ 可选依赖在顶层 import，不用也会装
