#!/usr/bin/env python3
"""preflight.py — python-quality-review 的零依赖预检扫描器。

纯标准库（ast）实现，拷到任何 Python 仓库即可运行，无需 pip install。
目的：在人工深读之前，快速、客观地锁定值得做质量提升的点。

用法：
    python preflight.py <path> [--json] [--min-severity P1]

输出按 P0/P1/P2 分级，每条可定位到 file:line。
退出码：有 P0/P1 时为 1，否则为 0（方便接 CI）。
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

# ---- 阈值（与 references/ 各清单保持一致）----
IF_ELIF_BRANCH_THRESHOLD = 5        # if-elif 类型分发链分支数
GOD_CLASS_LINES = 1000              # 上帝类行数
GOD_FUNCTION_LINES = 80            # 超长函数
PUBLIC_API_MODULE_THRESHOLD = 7    # 模块公共 API 数
MIN_SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def severity_rank(s: str) -> int:
    return MIN_SEVERITY_ORDER.get(s, 9)


class Finding:
    __slots__ = ("severity", "check", "file", "line", "symbol", "message")

    def __init__(self, severity, check, file, line, symbol, message):
        self.severity = severity
        self.check = check
        self.file = file
        self.line = line
        self.symbol = symbol
        self.message = message

    def as_dict(self):
        return {
            "severity": self.severity,
            "check": self.check,
            "file": self.file,
            "line": self.line,
            "symbol": self.symbol,
            "message": self.message,
        }


# ----------------------------------------------------------------------
# 检测器：每个返回 Finding 列表
# ----------------------------------------------------------------------

def check_private_penetration(tree: ast.AST, rel: str) -> list[Finding]:
    """维度二：访问 obj._private（obj 不是 self/cls/super 时）。"""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if not node.attr.startswith("_") or node.attr.startswith("__"):
            continue
        # 跳过 self._ / cls._（同类内部，合理）
        if isinstance(node.value, ast.Name) and node.value.id in ("self", "cls"):
            continue
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) \
                and node.value.func.id == "super":
            continue
        out.append(Finding(
            "P1", "封装穿透", rel, node.lineno, node.attr,
            f"跨对象访问私有属性 `{ast.unparse(node.value)}.{node.attr}`",
        ))
    return out


def check_internal_imports(tree: ast.AST, rel: str) -> list[Finding]:
    """维度二/三：from B import _internal（跨模块拿内部符号）。"""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        for alias in node.names:
            if alias.name.startswith("_") and alias.name != "__all__":
                out.append(Finding(
                    "P1", "内部符号外泄", rel, node.lineno, alias.name,
                    f"from {node.module or '?'} import {alias.name}（导入了下划线内部符号）",
                ))
    return out


def check_monkey_patch(tree: ast.AST, rel: str) -> list[Finding]:
    """维度二：模块级 Class.method = func（动态挂载/猴子补丁）。"""
    out = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                if target.attr.isidentifier():
                    out.append(Finding(
                        "P0", "猴子补丁", rel, node.lineno, f"{target.value.id}.{target.attr}",
                        f"模块级动态挂载 `{target.value.id}.{target.attr} = ...`，建议移进类体",
                    ))
    return out


def check_if_elif_chain(tree: ast.AST, rel: str) -> list[Finding]:
    """维度四：if-elif 类型分发链过长。只在链起点（非外层 orelse 的 If）报告一次。"""
    out = []
    # 收集所有「位于某个 If 的 orelse 里」的 If——它们是链的延续，不是起点
    nested_in_orelse: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        for item in node.orelse:
            if isinstance(item, ast.If):
                nested_in_orelse.add(id(item))
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or id(node) in nested_in_orelse:
            continue
        branches = 1
        cur = node
        while cur.orelse and len(cur.orelse) == 1 and isinstance(cur.orelse[0], ast.If):
            branches += 1
            cur = cur.orelse[0]
        if branches >= IF_ELIF_BRANCH_THRESHOLD:
            out.append(Finding(
                "P2", "if-elif分发链", rel, node.lineno, "",
                f"{branches} 个分支的类型分发链，建议改为注册表/字典映射",
            ))
    return out


def check_bare_except(tree: ast.AST, rel: str) -> list[Finding]:
    """维度一：裸 except / except Exception 过宽。"""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            out.append(Finding(
                "P0", "裸except", rel, node.lineno, "",
                "裸 `except:` 会捕获 KeyboardInterrupt/SystemExit，应指定具体异常",
            ))
        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
            out.append(Finding(
                "P2", "过宽except", rel, node.lineno, "",
                "`except Exception` 过宽，建议收窄为具体异常",
            ))
    return out


def check_god_units(tree: ast.AST, rel: str) -> list[Finding]:
    """维度一/三：超长类、超长函数、公共 API 过多的模块。"""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            length = (node.end_lineno or node.lineno) - node.lineno
            if length >= GOD_CLASS_LINES:
                out.append(Finding(
                    "P1", "上帝类", rel, node.lineno, node.name,
                    f"类 {length} 行（阈值 {GOD_CLASS_LINES}），疑似职责过多",
                ))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = (node.end_lineno or node.lineno) - node.lineno
            if length >= GOD_FUNCTION_LINES:
                out.append(Finding(
                    "P2", "超长函数", rel, node.lineno, node.name,
                    f"函数 {length} 行（阈值 {GOD_FUNCTION_LINES}），建议拆分",
                ))
    # 模块公共 API 数
    public = [n for n in tree.body
              if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
              and not n.name.startswith("_")]
    if len(public) >= PUBLIC_API_MODULE_THRESHOLD:
        out.append(Finding(
            "P2", "模块职责过宽", rel, 1, "",
            f"模块顶层公共定义 {len(public)} 个（阈值 {PUBLIC_API_MODULE_THRESHOLD}），可能应拆分",
        ))
    return out


def check_fake_classes(tree: ast.AST, rel: str) -> list[Finding]:
    """维度三：假类——全是 staticmethod/classmethod，无实例状态。"""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        methods = [n for n in node.body
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if not methods:
            continue
        static_like = 0
        has_init_state = False
        for m in methods:
            decos = [getattr(d, "id", "") or getattr(d, "attr", "") for d in m.decorator_list]
            if m.name in ("__init__", "__post_init__"):
                has_init_state = True
            if "staticmethod" in decos or "classmethod" in decos:
                static_like += 1
        if methods and static_like == len(methods) and not has_init_state:
            out.append(Finding(
                "P2", "假类", rel, node.lineno, node.name,
                f"类 {node.name} 全部是 staticmethod/classmethod、无实例状态，"
                f"本质是命名空间，建议降为模块级函数",
            ))
    return out


# 检测器注册表：(函数, 维度)
DETECTORS = [
    check_private_penetration,
    check_internal_imports,
    check_monkey_patch,
    check_if_elif_chain,
    check_bare_except,
    check_god_units,
    check_fake_classes,
]


def iter_py_files(root: Path):
    for p in sorted(root.rglob("*.py")):
        parts = p.parts
        if any(part in ("__pycache__", ".venv", "venv", ".git", "build", "dist")
               for part in parts):
            continue
        yield p


def scan_file(path: Path, root: Path) -> list[Finding]:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return [Finding("P3", "语法错误", str(path), 0, "", "无法解析（语法错误，跳过）")]
    rel = str(path.relative_to(root))
    out = []
    for det in DETECTORS:
        out.extend(det(tree, rel))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="python-quality-review 零依赖预检")
    ap.add_argument("path", help="要扫描的 Python 项目路径")
    ap.add_argument("--json", action="store_true", help="输出 JSON（默认输出表格）")
    ap.add_argument("--min-severity", default="P2", choices=list(MIN_SEVERITY_ORDER),
                    help="只输出 >= 该级别的问题（默认 P2）")
    args = ap.parse_args(argv)

    root = Path(args.path).resolve()
    if not root.exists():
        print(f"路径不存在: {root}", file=sys.stderr)
        return 2

    findings = []
    py_count = 0
    for py in iter_py_files(root):
        py_count += 1
        findings.extend(scan_file(py, root))

    threshold = severity_rank(args.min_severity)
    findings = [f for f in findings if severity_rank(f.severity) <= threshold]
    findings.sort(key=lambda f: (severity_rank(f.severity), f.file, f.line))

    if args.json:
        print(json.dumps({
            "root": str(root),
            "python_files": py_count,
            "count": len(findings),
            "findings": [f.as_dict() for f in findings],
        }, ensure_ascii=False, indent=2))
    else:
        print(f"预检：{root}（扫描 {py_count} 个 .py 文件，{len(findings)} 个问题）\n")
        by_sev = defaultdict(list)
        for f in findings:
            by_sev[f.severity].append(f)
        for sev in ("P0", "P1", "P2", "P3"):
            items = by_sev.get(sev)
            if not items:
                continue
            print(f"### {sev}（{len(items)}）")
            for f in items:
                sym = f" `{f.symbol}`" if f.symbol else ""
                print(f"  {f.file}:{f.line}  [{f.check}]{sym}  {f.message}")
            print()

    has_blocking = any(severity_rank(f.severity) <= 1 for f in findings)
    return 1 if has_blocking else 0


if __name__ == "__main__":
    sys.exit(main())
