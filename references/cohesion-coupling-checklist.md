# 高内聚低耦合 + 游离方法检查清单

## 一、高内聚判定

> 一个模块/类只做一件事，修改它只有一个理由。

### 检查方法

1. **读模块 docstring**：如果一句话说不清楚这个模块做什么，可能内聚不够
2. **数公共 API**：一个模块公共类/函数超过 7 个，可能职责过多
3. **LCOM（方法内聚缺乏度）**：类的方法是否都在操作同一组属性

### 高内聚的信号
- ✅ 类名准确描述了它的全部职责
- ✅ 大部分方法都在访问大部分属性
- ✅ 修改一个功能只需要改一个类/模块
- ✅ 类有清晰的"单一职责"

### 低内聚的信号
- ❌ 类名含 `Manager`、`Helper`、`Util`、`Handler`（太泛）
- ❌ 一个类有 10+ 个公共方法
- ❌ 修改一个功能需要改好几个不相关的方法
- ❌ 上帝类（>1000 行，什么都做）

---

## 二、低耦合判定

> 模块之间通过公共 API 交互，不依赖内部实现细节。

### 检查方法

1. **画依赖图**：模块 A 依赖模块 B 的哪些东西？
2. **数 import**：一个模块 import 了多少其他模块的内部符号？
3. **改一处波及范围**：改一个类，需要联动改多少个其他文件？

### 低耦合的信号
- ✅ 模块之间通过接口/抽象类交互，不依赖具体实现
- ✅ 依赖方向清晰（上层依赖下层抽象）
- ✅ 改一个模块的内部实现，不需要改其他模块
- ✅ 每个模块有明确的"公共 API 面"

### 高耦合的信号
- ❌ A 模块直接访问 B 模块对象的私有属性
- ❌ A 模块 import 了 B 模块的内部符号（`_` 前缀的东西）
- ❌ 修改一个简单的功能要改 5+ 个文件
- ❌ 循环依赖

---

## 三、游离方法识别

> 操作某对象的行为，却定义在对象之外。

### 五类游离方法

#### 类型 1：模块级函数操作某类实例
**特征**：函数第一个参数就是某类实例，函数内部大量访问该实例的属性/方法。

```python
# ❌ 游离：逻辑属于 RequestContext，但定义在外面
def extract_llm_params(ctx: RequestContext) -> LLMParams | None:
    return getattr(ctx, "last_llm_params", None)

# ✅ 归位：变成类的方法/属性
class RequestContext:
    @property
    def last_llm_params(self) -> LLMParams | None:
        return self._last_llm_params
```

**判定方法**：扫描所有模块级函数，看第一个参数的类型是不是某个类。

#### 类型 2：自由函数 + 猴子补丁
**特征**：函数定义在类体外，然后 `Class.method = func` 动态挂载。

```python
# ❌ 游离：猴子补丁
def _from_client(cls, client):
    ...

AgentApp.from_client = classmethod(_from_client)

# ✅ 归位：移进类体
class AgentApp:
    @classmethod
    def from_client(cls, client: Any) -> "AgentApp":
        ...
```

#### 类型 3：utils 里的专用函数
**特征**：放在 utils/ 里，但只被一个类/模块使用，逻辑上就是那个类的行为。

```python
# ❌ 游离：tool_call_to_dict 只在 response 模块用，且操作 ToolCall
# utils/format.py
def tool_call_to_dict(tc: Any) -> dict[str, Any]:
    if isinstance(tc, dict):
        return tc
    return {"name": tc.name, "args": tc.args, "id": tc.id}

# ✅ 归位：移到 response/serialization.py，变成模块级工具或类方法
```

**判定方法**：grep 函数名的调用点，如果调用点都集中在同一个模块，考虑归位。

#### 类型 4：跨模块直操内部状态（最严重）
**特征**：A 模块的函数直接读写 B 模块对象的 `_` 前缀属性。这不仅是游离，更是封装破坏。

```python
# ❌ 游离 + 封装破坏：register 逻辑散落在外
def build_app(registry: AgentRegistry) -> None:
    # 绕过 registry.register()，直接写内部字典
    registry._agents["default"] = AgentInstance(...)

# ✅ 归位：给 AgentRegistry 加批量注册方法
class AgentRegistry:
    def register_many(self, agents: dict[str, AgentInstance]) -> None:
        ...
```

#### 类型 5：假类（全 staticmethod 的命名空间）
**特征**：一个类全是 `@staticmethod`，没有任何实例状态。本质是用类当命名空间，不是真正的 OOP。

```python
# ⚠️ 游离：假类
class BusKeys:
    @staticmethod
    def wakeup_queue(agent_id: str | None = None) -> str: ...

    @staticmethod
    def session_events(agent_id: str | None = None) -> str: ...
```

**判定**：这类不算严重问题。如果函数之间确实是一组相关的工具，用类当命名空间也合理。但如果是为了"显得 OOP"而套壳，不如直接用模块级函数。

---

## 四、游离程度分级

| 级别 | 类型 | 严重度 | 修复优先级 |
|------|------|--------|-----------|
| L1 | 跨模块直操内部状态（类型 4） | 🔴 高 | P0 |
| L2 | 自由函数 + 猴子补丁（类型 2） | 🟠 中 | P1 |
| L3 | 模块级函数操作某类实例（类型 1） | 🟠 中 | P1 |
| L4 | utils 里的专用函数（类型 3） | 🟡 低 | P2 |
| L5 | 假类 / 命名空间类（类型 5） | 🟢 低 | 可不动 |

---

## 五、分析步骤

审查一个模块/项目时，按以下步骤找游离方法：

1. **扫模块级函数**：`grep "^def "` 找所有顶层函数
2. **看第一个参数**：如果第一个参数的类型是某个类，标记为候选
3. **查调用点**：grep 函数名，看在哪里被调用，调用频率
4. **查归属**：这个函数逻辑上属于哪个对象？
5. **查封装破坏**：`grep "\._[a-z]"` 找所有私有属性访问，排除同一类内的
6. **查猴子补丁**：`grep "Classname\."` 在类定义之外的赋值

---

## 六、修复原则

1. **能归位就归位**：逻辑属于哪个类，就放到哪个类里
2. **不能归位的就近放**：如果涉及多个类，放在主要操作的那个类里，或放协调者类
3. **纯工具函数不强行归位**：真正无状态、被多处复用的纯函数，放 utils 没问题
4. **假类不必强拆**：用类当命名空间是合理的，除非有明确的更好去处
