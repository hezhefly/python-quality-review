# 封装边界审查清单

参照成熟开源项目「封装严谨、公共/内部边界明确」的设计原则。

## 核心原则

> 一个模块/类暴露给外部的，应该是它**愿意**暴露的，而不是外部**能够**访问到的。

## 1. 私有属性穿透

### 检查方法
全局搜索 `._[a-z]`（访问 `_` 开头的属性），排除同一类/同一模块内的访问。

### 红线（零容忍）
- ❌ A 类方法直接访问 B 类的 `_` 前缀属性
- ❌ 用 `# noqa: SLF001` 压制封装告警
- ❌ 直接操作其他对象的内部字典/列表（绕过公共 API）

### 典型反模式
```python
# ❌ 错误：绕过 register() 直接写内部字典
registry._agents[agent_id] = AgentInstance(...)

# ❌ 错误：用 noqa 压制
# noqa: SLF001
count = len(registry._agents)

# ✅ 正确：通过公共方法
registry.register(agent_id, instance)
count = registry.count()
```

### 修复方法
1. 给被访问的类补充对应的公共方法/property
2. 外部调用改为走公共 API
3. 删除 `# noqa: SLF001`

## 2. 猴子补丁 / 动态挂载

### 检查方法
搜索 `Classname.method = `、`classmethod(`、`staticmethod(` 在类定义之外的使用。

### 红线
- ❌ 类体之外定义函数，然后 `Class.method = func` 动态挂载
- ❌ `Class.class_method = classmethod(_func)` 猴子补丁

### 为什么不好
- IDE 补全看不到，静态分析漏检
- 读者翻完整篇类定义，还不知道类有哪些方法
- 新增类特性时容易忽略补丁方法

### 修复方法
- **优先**：移进类体，作为真正的方法
- **如果必须延迟加载**：类体内声明占位方法，内部委托到实现函数
- **如果为了可选依赖**：在类内用 `try/except ImportError` 惰性导入，方法内判断

```python
# ✅ 方案 A：类体内声明 + 惰性导入
class AgentApp:
    @classmethod
    def from_client(cls, client: Any) -> "AgentApp":
        from ._client_adapter import _from_client
        return _from_client(cls, client)
```

## 3. 公共/内部边界

### `__init__.py` 规范
每个包的 `__init__.py` 必须：
1. 有 docstring 说明这个包做什么
2. 显式 import 要导出的公共符号
3. 有 `__all__` 白名单，与 import 一一对应

```python
# ✅ 标准模式
"""Agent 核心模块。"""

from ._app import AgentApp
from ._executor import GraphExecutor

__all__ = ["AgentApp", "GraphExecutor"]
```

### 内部模块命名
- 不对外暴露的实现模块 → 文件名加 `_` 前缀（`_executor.py`、`_registry.py`）
- 纯数据/资源目录 → 不加 `__init__.py`，文件系统层面挡住 import

### 检查项
| 检查项 | 标准 |
|--------|------|
| `__all__` 存在率 | 每个有公共 API 的包都有 |
| 内部模块 `_` 前缀率 | 实现细节模块 ≥ 80% |
| 外部直接 import 内部模块 | 0 次（必须通过包级 API） |

## 4. 属性 vs 方法的边界

### 公共属性
- 纯数据字段（Pydantic / dataclass）→ 直接暴露属性
- 不应该从外部修改的状态 → `@property`（只读）

### 私有属性
- 类的内部状态 → `_` 前缀
- 子类也不应该碰的 → `__` 双前缀（极少用）

### 反模式
```python
# ❌ 错误：用属性暴露可变内部状态
class Registry:
    agents: dict[str, AgentInstance]  # 外部可直接改

# ✅ 正确：通过方法操作，内部状态封装
class Registry:
    _agents: dict[str, AgentInstance]  # 私有

    def register(self, agent_id: str, instance: AgentInstance) -> None: ...
    def get(self, agent_id: str) -> AgentInstance | None: ...
    def count(self) -> int: ...
```

## 5. 全局变量 / 模块状态

### 红线
- ❌ 模块级可变全局变量被外部直接修改
- ❌ 用全局变量传递上下文（应该用函数参数或 contextvar）

### 合格模式
- 模块级常量 → 全大写 + 不变
- 模块级单例 → 通过工厂函数/`get_instance()` 访问，不直接暴露变量
- 上下文传递 → 用 `contextvars.ContextVar`

## AgentScope 标杆

AgentScope 在封装上的做法：
1. **内部模块全部 `_` 前缀**：`_agent.py`、`_model.py`、`_factory.py`、`_utils.py`
2. **每个 `__init__.py` 都有 `__all__`**：公共 API 白名单清晰
3. **基类严格 protected**：`_call_api`、`_format_tools`、`_stream` 等钩子方法都是 `_` 前缀，子类实现但外部不调用
4. **从不穿透封装**：外部模块只通过公共 API 交互，没有 `noqa: SLF001`
