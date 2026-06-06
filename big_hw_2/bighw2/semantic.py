"""Semantic analysis for the Class-Rust AST.

This module is intentionally separate from parser.py: the parser owns syntax
and AST construction, while this module owns semantic checks and, later,
intermediate-code generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from diagnostics import Diagnostic, SourceLoc
from parser import (
    UNKNOWN,
    I32,
    ArrayExpr,
    AssignStmt,
    BinaryExpr,
    Block,
    BlockExpr,
    BreakStmt,
    CallExpr,
    ContinueStmt,
    EmptyStmt,
    Expr,
    ExprBlock,
    ExprStmt,
    FieldExpr,
    ForStmt,
    FunctionDecl,
    IdentExpr,
    IfExpr,
    IfStmt,
    IndexExpr,
    LetStmt,
    LoopExpr,
    LoopStmt,
    NumExpr,
    Program,
    RangeExpr,
    ReturnStmt,
    Stmt,
    TupleExpr,
    TypeArray,
    TypeI32,
    TypeNode,
    TypeRef,
    TypeTuple,
    TypeUnknown,
    UnaryExpr,
    WhileStmt,
)


@dataclass
class VarInfo:
    mutable: bool
    type_node: TypeNode


@dataclass
class SemanticResult:
    errors: List[str] = field(default_factory=list)
    diagnostics: List[Diagnostic] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "errors": self.errors,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


class SemanticAnalyzer:
    """Walk the AST and report semantic errors with source locations."""

    def __init__(self):
        self.errors: List[str] = []
        self.diagnostics: List[Diagnostic] = []
        self.scopes: List[dict[str, VarInfo]] = []
        self.current_return_type: Optional[TypeNode] = None
        self.loop_break_types: List[List[TypeNode]] = []

    def analyze(self, program: Program) -> SemanticResult:
        self._reset()
        for fn in program.functions:
            self._check_function(fn)
        return SemanticResult(
            errors=list(self.errors),
            diagnostics=list(self.diagnostics),
        )

    def check(self, program: Program) -> List[str]:
        return self.analyze(program).errors

    def _reset(self) -> None:
        self.errors = []
        self.diagnostics = []
        self.scopes = []
        self.current_return_type = None
        self.loop_break_types = []

    def _report(self, message: str, loc: Optional[SourceLoc] = None) -> None:
        diagnostic = Diagnostic.from_loc("semantic", message, loc or SourceLoc())
        self.diagnostics.append(diagnostic)
        self.errors.append(diagnostic.format())

    # ---------- scope helpers ----------

    def _push_scope(self) -> None:
        self.scopes.append({})

    def _pop_scope(self) -> None:
        self.scopes.pop()

    def _declare(self, name: str, var: VarInfo, loc: Optional[SourceLoc] = None) -> None:
        if not self.scopes:
            self._push_scope()
        cur = self.scopes[-1]
        if name in cur:
            self._report(f"变量 '{name}' 在同一作用域重复定义", loc)
            return
        cur[name] = var

    def _lookup(self, name: str) -> Optional[VarInfo]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    # ---------- type helpers ----------

    def _type_str(self, t: TypeNode) -> str:
        if isinstance(t, TypeI32):
            return "i32"
        if isinstance(t, TypeRef):
            prefix = "&mut " if t.mutable else "&"
            return prefix + self._type_str(t.inner)
        if isinstance(t, TypeArray):
            return f"[{self._type_str(t.inner)};{t.size}]"
        if isinstance(t, TypeTuple):
            return "(" + ",".join(self._type_str(x) for x in t.items) + ")"
        return "unknown"

    def _compatible(self, expected: TypeNode, actual: TypeNode) -> bool:
        if isinstance(expected, TypeUnknown) or isinstance(actual, TypeUnknown):
            return True

        if isinstance(expected, TypeI32):
            return isinstance(actual, TypeI32)

        if isinstance(expected, TypeRef):
            if not isinstance(actual, TypeRef):
                return False
            return expected.mutable == actual.mutable and self._compatible(expected.inner, actual.inner)

        if isinstance(expected, TypeArray):
            if not isinstance(actual, TypeArray):
                return False
            return expected.size == actual.size and self._compatible(expected.inner, actual.inner)

        if isinstance(expected, TypeTuple):
            if not isinstance(actual, TypeTuple):
                return False
            if len(expected.items) != len(actual.items):
                return False
            return all(self._compatible(a, b) for a, b in zip(expected.items, actual.items))

        return True

    # ---------- entry ----------

    def _check_function(self, fn: FunctionDecl) -> None:
        self._push_scope()
        for p in fn.params:
            self._declare(p.name, VarInfo(mutable=p.mutable, type_node=p.type_node), p.loc)

        prev_ret = self.current_return_type
        self.current_return_type = fn.return_type

        body_tail_type = self._check_expr_block(fn.body)
        if fn.return_type is not None and fn.body.tail_expr is not None:
            if not self._compatible(fn.return_type, body_tail_type):
                self._report(
                    f"函数 '{fn.name}' 尾表达式类型 {self._type_str(body_tail_type)} "
                    f"与返回类型 {self._type_str(fn.return_type)} 不匹配",
                    fn.body.tail_expr.loc,
                )

        self.current_return_type = prev_ret
        self._pop_scope()

    # ---------- statement checks ----------

    def _check_block(self, block: Block) -> None:
        self._push_scope()
        for stmt in block.statements:
            self._check_stmt(stmt)
        self._pop_scope()

    def _check_expr_block(self, block: ExprBlock) -> TypeNode:
        self._push_scope()
        for stmt in block.statements:
            self._check_stmt(stmt)

        tail_type: TypeNode = UNKNOWN
        if block.tail_expr is not None:
            tail_type = self._infer_expr(block.tail_expr)

        self._pop_scope()
        return tail_type

    def _check_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, EmptyStmt):
            return

        if isinstance(stmt, ExprStmt):
            self._infer_expr(stmt.expr)
            return

        if isinstance(stmt, ReturnStmt):
            if stmt.value is None:
                if self.current_return_type is not None:
                    self._report("函数声明了返回类型，但 return 缺少返回值", stmt.loc)
                return

            val_type = self._infer_expr(stmt.value)
            if self.current_return_type is not None and not self._compatible(self.current_return_type, val_type):
                self._report(
                    f"return 类型 {self._type_str(val_type)} 与函数返回类型 "
                    f"{self._type_str(self.current_return_type)} 不匹配",
                    stmt.loc,
                )
            return

        if isinstance(stmt, LetStmt):
            init_type = self._infer_expr(stmt.init) if stmt.init is not None else UNKNOWN

            if stmt.annotation is not None and stmt.init is not None:
                if not self._compatible(stmt.annotation, init_type):
                    self._report(
                        f"变量 '{stmt.name}' 声明类型 {self._type_str(stmt.annotation)} "
                        f"与初始化类型 {self._type_str(init_type)} 不匹配",
                        stmt.loc,
                    )

            final_type = stmt.annotation if stmt.annotation is not None else init_type
            self._declare(stmt.name, VarInfo(mutable=stmt.mutable, type_node=final_type), stmt.loc)
            return

        if isinstance(stmt, AssignStmt):
            lhs_type, lhs_mutable = self._infer_assign_target(stmt.target)
            rhs_type = self._infer_expr(stmt.value)

            if not lhs_mutable:
                self._report("对不可变左值进行赋值", stmt.loc)

            if not self._compatible(lhs_type, rhs_type):
                self._report(
                    f"赋值两侧类型不匹配，左侧为 {self._type_str(lhs_type)}，"
                    f"右侧为 {self._type_str(rhs_type)}",
                    stmt.loc,
                )
            return

        if isinstance(stmt, IfStmt):
            self._infer_expr(stmt.condition)
            self._check_block(stmt.then_block)
            if isinstance(stmt.else_branch, Block):
                self._check_block(stmt.else_branch)
            elif isinstance(stmt.else_branch, IfStmt):
                self._check_stmt(stmt.else_branch)
            return

        if isinstance(stmt, WhileStmt):
            self._infer_expr(stmt.condition)
            self.loop_break_types.append([])
            self._check_block(stmt.body)
            self.loop_break_types.pop()
            return

        if isinstance(stmt, ForStmt):
            iterable_elem_type = UNKNOWN

            if isinstance(stmt.iterable, RangeExpr):
                self._infer_expr(stmt.iterable.start)
                self._infer_expr(stmt.iterable.end)
                iterable_elem_type = I32
            else:
                iterable_type = self._infer_expr(stmt.iterable)
                if isinstance(iterable_type, TypeArray):
                    iterable_elem_type = iterable_type.inner
                else:
                    self._report("for 循环仅允许遍历区间表达式或数组表达式", stmt.iterable.loc)

            loop_var_type = stmt.var_type if stmt.var_type is not None else iterable_elem_type
            if stmt.var_type is not None and not isinstance(iterable_elem_type, TypeUnknown):
                if not self._compatible(stmt.var_type, iterable_elem_type):
                    self._report(
                        f"for 迭代变量 '{stmt.var_name}' 类型 "
                        f"{self._type_str(stmt.var_type)} 与可迭代元素类型 "
                        f"{self._type_str(iterable_elem_type)} 不匹配",
                        stmt.loc,
                    )

            self._push_scope()
            self._declare(stmt.var_name, VarInfo(mutable=stmt.var_mutable, type_node=loop_var_type), stmt.loc)
            self.loop_break_types.append([])
            for body_stmt in stmt.body.statements:
                self._check_stmt(body_stmt)
            self.loop_break_types.pop()
            self._pop_scope()
            return

        if isinstance(stmt, LoopStmt):
            self.loop_break_types.append([])
            self._check_block(stmt.body)
            self.loop_break_types.pop()
            return

        if isinstance(stmt, BreakStmt):
            if not self.loop_break_types:
                self._report("break 只能出现在循环中", stmt.loc)
                return
            if stmt.value is not None:
                self.loop_break_types[-1].append(self._infer_expr(stmt.value))
            return

        if isinstance(stmt, ContinueStmt):
            if not self.loop_break_types:
                self._report("continue 只能出现在循环中", stmt.loc)
            return

    # ---------- expression/type inference ----------

    def _infer_assign_target(self, expr: Expr) -> Tuple[TypeNode, bool]:
        if isinstance(expr, IdentExpr):
            info = self._lookup(expr.name)
            if info is None:
                self._report(f"未定义变量 '{expr.name}'", expr.loc)
                return UNKNOWN, False
            return info.type_node, info.mutable

        if isinstance(expr, UnaryExpr) and expr.op == "*":
            base_type = self._infer_expr(expr.operand)
            if isinstance(base_type, TypeRef):
                return base_type.inner, base_type.mutable
            self._report("解引用赋值目标不是引用类型", expr.loc)
            return UNKNOWN, False

        if isinstance(expr, IndexExpr):
            base_type = self._infer_expr(expr.base)
            mutable = self._is_mutable_lvalue(expr.base)
            if isinstance(base_type, TypeArray):
                self._infer_expr(expr.index)
                return base_type.inner, mutable
            self._report("下标赋值目标不是数组", expr.loc)
            return UNKNOWN, False

        if isinstance(expr, FieldExpr):
            base_type = self._infer_expr(expr.base)
            mutable = self._is_mutable_lvalue(expr.base)
            if isinstance(base_type, TypeTuple):
                if 0 <= expr.index < len(base_type.items):
                    return base_type.items[expr.index], mutable
                self._report("元组点访问越界", expr.loc)
                return UNKNOWN, mutable
            self._report("点访问赋值目标不是元组", expr.loc)
            return UNKNOWN, mutable

        self._report("非法赋值左值", getattr(expr, "loc", SourceLoc()))
        return UNKNOWN, False

    def _is_mutable_lvalue(self, expr: Expr) -> bool:
        if isinstance(expr, IdentExpr):
            info = self._lookup(expr.name)
            return info.mutable if info is not None else False

        if isinstance(expr, UnaryExpr) and expr.op == "*":
            base_type = self._infer_expr(expr.operand)
            return isinstance(base_type, TypeRef) and base_type.mutable

        if isinstance(expr, IndexExpr):
            return self._is_mutable_lvalue(expr.base)

        if isinstance(expr, FieldExpr):
            return self._is_mutable_lvalue(expr.base)

        return False

    def _infer_expr(self, expr: Optional[Expr]) -> TypeNode:
        if expr is None:
            return UNKNOWN

        if isinstance(expr, NumExpr):
            return I32

        if isinstance(expr, IdentExpr):
            info = self._lookup(expr.name)
            if info is None:
                self._report(f"使用了未定义变量 '{expr.name}'", expr.loc)
                return UNKNOWN
            return info.type_node

        if isinstance(expr, UnaryExpr):
            operand_type = self._infer_expr(expr.operand)
            if expr.op == "&":
                return TypeRef(inner=operand_type, mutable=False)
            if expr.op == "&mut":
                return TypeRef(inner=operand_type, mutable=True)
            if expr.op == "*":
                if isinstance(operand_type, TypeRef):
                    return operand_type.inner
                self._report("解引用操作数不是引用", expr.loc)
                return UNKNOWN
            return UNKNOWN

        if isinstance(expr, BinaryExpr):
            left_type = self._infer_expr(expr.left)
            right_type = self._infer_expr(expr.right)

            if expr.op in {"+", "-", "*", "/"}:
                if not self._compatible(left_type, I32) or not self._compatible(right_type, I32):
                    self._report("算术运算要求两侧为 i32", expr.loc)
                return I32

            if expr.op in {"<", "<=", ">", ">=", "==", "!="}:
                if not self._compatible(left_type, right_type):
                    self._report("比较运算两侧类型不兼容", expr.loc)
                return I32

            return UNKNOWN

        if isinstance(expr, CallExpr):
            for a in expr.args:
                self._infer_expr(a)
            # Function signature table will be added in the next semantic pass.
            return UNKNOWN

        if isinstance(expr, ArrayExpr):
            if not expr.elements:
                return TypeArray(inner=UNKNOWN, size=0)

            first_type = self._infer_expr(expr.elements[0])
            for e in expr.elements[1:]:
                et = self._infer_expr(e)
                if not self._compatible(first_type, et):
                    self._report("数组字面量元素类型不一致", e.loc)
            return TypeArray(inner=first_type, size=len(expr.elements))

        if isinstance(expr, TupleExpr):
            return TypeTuple(items=tuple(self._infer_expr(e) for e in expr.elements))

        if isinstance(expr, IndexExpr):
            base_type = self._infer_expr(expr.base)
            self._infer_expr(expr.index)
            if isinstance(base_type, TypeArray):
                return base_type.inner
            self._report("仅数组支持下标访问", expr.loc)
            return UNKNOWN

        if isinstance(expr, FieldExpr):
            base_type = self._infer_expr(expr.base)
            if isinstance(base_type, TypeTuple):
                if 0 <= expr.index < len(base_type.items):
                    return base_type.items[expr.index]
                self._report("元组索引越界", expr.loc)
                return UNKNOWN
            self._report("仅元组支持 .<NUM> 访问", expr.loc)
            return UNKNOWN

        if isinstance(expr, BlockExpr):
            return self._check_expr_block(expr.block)

        if isinstance(expr, IfExpr):
            self._infer_expr(expr.condition)
            t1 = self._check_expr_block(expr.then_block)
            t2 = self._check_expr_block(expr.else_block)
            if self._compatible(t1, t2):
                return t1
            self._report("if 表达式两个分支类型不一致", expr.loc)
            return UNKNOWN

        if isinstance(expr, LoopExpr):
            self.loop_break_types.append([])
            self._check_block(expr.body)
            breaks = self.loop_break_types.pop()
            if not breaks:
                return UNKNOWN
            base = breaks[0]
            for t in breaks[1:]:
                if not self._compatible(base, t):
                    self._report("loop 表达式 break 的值类型不一致", expr.loc)
                    return UNKNOWN
            return base

        if isinstance(expr, RangeExpr):
            self._infer_expr(expr.start)
            self._infer_expr(expr.end)
            return UNKNOWN

        return UNKNOWN


SemanticChecker = SemanticAnalyzer
