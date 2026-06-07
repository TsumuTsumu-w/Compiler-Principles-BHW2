"""Class-Rust recursive-descent parser and AST definitions.

This module builds on lexer.py and implements the recursive-descent parser
for grammar rules 0.1~9.3 in the handout, plus the AST node definitions and
AST rendering helpers. Semantic analysis and intermediate-code generation
live in semantic.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields as dataclass_fields, is_dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import argparse
import json
import sys

try:
    from lexer import Lexer, Token, TokenType
    from diagnostics import Diagnostic, SourceLoc
except ModuleNotFoundError:
    # Fallback for package-style execution.
    from bighw2.lexer import Lexer, Token, TokenType
    from bighw2.diagnostics import Diagnostic, SourceLoc


# ==================== AST: Types ====================


class TypeNode:
    """Base class for type nodes."""


@dataclass(frozen=True)
class TypeI32(TypeNode):
    pass


@dataclass(frozen=True)
class TypeRef(TypeNode):
    inner: TypeNode
    mutable: bool = False


@dataclass(frozen=True)
class TypeArray(TypeNode):
    inner: TypeNode
    size: int


@dataclass(frozen=True)
class TypeTuple(TypeNode):
    items: Tuple[TypeNode, ...]


@dataclass(frozen=True)
class TypeUnknown(TypeNode):
    reason: str = "unknown"


I32 = TypeI32()
UNKNOWN = TypeUnknown()


# ==================== AST: Expressions ====================


class Expr:
    """Base class for expression nodes."""


@dataclass
class NumExpr(Expr):
    value: int
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class IdentExpr(Expr):
    name: str
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class UnaryExpr(Expr):
    op: str
    operand: Expr
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class BinaryExpr(Expr):
    op: str
    left: Expr
    right: Expr
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class CallExpr(Expr):
    callee: Expr
    args: List[Expr]
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class ArrayExpr(Expr):
    elements: List[Expr]
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class TupleExpr(Expr):
    elements: List[Expr]
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class IndexExpr(Expr):
    base: Expr
    index: Expr
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class FieldExpr(Expr):
    base: Expr
    index: int
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class BlockExpr(Expr):
    block: "ExprBlock"
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class IfExpr(Expr):
    condition: Expr
    then_block: "ExprBlock"
    else_block: "ExprBlock"
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class LoopExpr(Expr):
    body: "Block"
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class RangeExpr(Expr):
    start: Expr
    end: Expr
    loc: SourceLoc = field(default_factory=SourceLoc)


# ==================== AST: Statements/Blocks ====================


class Stmt:
    """Base class for statement nodes."""


@dataclass
class EmptyStmt(Stmt):
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class ExprStmt(Stmt):
    expr: Expr
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class ReturnStmt(Stmt):
    value: Optional[Expr]
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class LetStmt(Stmt):
    name: str
    mutable: bool
    annotation: Optional[TypeNode]
    init: Optional[Expr]
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class AssignStmt(Stmt):
    target: Expr
    value: Expr
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_block: "Block"
    else_branch: Optional[Union["IfStmt", "Block"]]
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class WhileStmt(Stmt):
    condition: Expr
    body: "Block"
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class ForStmt(Stmt):
    var_name: str
    var_mutable: bool
    var_type: Optional[TypeNode]
    iterable: Expr
    body: "Block"
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class LoopStmt(Stmt):
    body: "Block"
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class BreakStmt(Stmt):
    value: Optional[Expr]
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class ContinueStmt(Stmt):
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class Block:
    statements: List[Stmt] = field(default_factory=list)
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class ExprBlock:
    statements: List[Stmt] = field(default_factory=list)
    tail_expr: Optional[Expr] = None
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class Param:
    name: str
    mutable: bool
    type_node: TypeNode
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class FunctionDecl:
    name: str
    params: List[Param]
    return_type: Optional[TypeNode]
    body: ExprBlock
    loc: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class Program:
    functions: List[FunctionDecl]
    loc: SourceLoc = field(default_factory=SourceLoc)


# ==================== Parser ====================


class ParseError(Exception):
    """Internal parser control-flow exception."""


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = list(tokens)
        self.index = 0
        self.errors: List[str] = []
        self.diagnostics: List[Diagnostic] = []

        # Normalize stream: always end with EOF sentinel for simpler parsing.
        if not self.tokens:
            self.tokens.append(Token(TokenType.EOF, "", 1, 1))
        elif self.tokens[-1].token_type != TokenType.EOF:
            last = self.tokens[-1]
            self.tokens.append(Token(TokenType.EOF, "", last.line, last.column))

    # ---------- stream helpers ----------

    def _current(self) -> Token:
        return self.tokens[self.index]

    def _previous(self) -> Token:
        return self.tokens[max(0, self.index - 1)]

    def _at_end(self) -> bool:
        return self._current().token_type == TokenType.EOF

    def _advance(self) -> Token:
        if not self._at_end():
            self.index += 1
        return self._previous()

    def _check(self, token_type: TokenType) -> bool:
        return self._current().token_type == token_type

    def _match(self, *types: TokenType) -> bool:
        cur_type = self._current().token_type
        for t in types:
            if cur_type == t:
                self._advance()
                return True
        return False

    def _consume(self, token_type: TokenType, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        self._raise_error(self._current(), message)
        raise ParseError()

    def _raise_error(self, token: Token, message: str) -> None:
        diagnostic = Diagnostic.from_token("syntax", message, token)
        self.diagnostics.append(diagnostic)
        self.errors.append(diagnostic.format())

    def _synchronize_top_level(self) -> None:
        while not self._at_end():
            if self._check(TokenType.KW_FN) or self._check(TokenType.HASH):
                return
            self._advance()

    _STMT_STARTERS = {
        TokenType.KW_LET, TokenType.KW_RETURN, TokenType.KW_IF,
        TokenType.KW_WHILE, TokenType.KW_FOR, TokenType.KW_LOOP,
        TokenType.KW_BREAK, TokenType.KW_CONTINUE,
        TokenType.LBRACE, TokenType.RBRACE,
    }

    def _synchronize_to_statement(self) -> None:
        """跳到下一个 ';' 或语句起始关键字/'}'，恢复到下一条语句。"""
        while not self._at_end():
            if self._check(TokenType.SEMI):
                self._advance()  # 吃掉分号
                return
            if self._current().token_type in self._STMT_STARTERS:
                return  # 停在下一条语句前，不消费
            self._advance()

    # ---------- top-level ----------

    def parse(self) -> Program:
        functions: List[FunctionDecl] = []
        program_loc = SourceLoc.from_token(self._current())

        while not self._at_end() and not self._check(TokenType.HASH):
            try:
                if self._check(TokenType.KW_FN):
                    functions.append(self._parse_function_decl())
                else:
                    self._raise_error(self._current(), "顶层只允许函数声明")
                    self._synchronize_top_level()
            except ParseError:
                self._synchronize_top_level()

        # Optional end marker '#'
        if self._check(TokenType.HASH):
            self._advance()

        return Program(functions, loc=program_loc)

    # ---------- declarations ----------

    def _parse_function_decl(self) -> FunctionDecl:
        self._consume(TokenType.KW_FN, "函数声明应以 fn 开始")
        name_token = self._consume(TokenType.IDENT, "fn 后应是函数名")
        name = name_token.value

        self._consume(TokenType.LPAREN, "函数名后缺少 '('")
        params: List[Param] = []
        if not self._check(TokenType.RPAREN):
            while True:
                params.append(self._parse_param())
                if not self._match(TokenType.COMMA):
                    break
        self._consume(TokenType.RPAREN, "形参列表缺少 ')'")

        ret_type: Optional[TypeNode] = None
        if self._match(TokenType.ARROW):
            ret_type = self._parse_type()

        body = self._parse_flexible_expr_block()
        return FunctionDecl(
            name=name,
            params=params,
            return_type=ret_type,
            body=body,
            loc=SourceLoc.from_token(name_token),
        )

    def _parse_param(self) -> Param:
        mutable = self._match(TokenType.KW_MUT)
        name_token = self._consume(TokenType.IDENT, "形参缺少标识符")
        name = name_token.value
        self._consume(TokenType.COLON, "形参缺少 ':'")
        type_node = self._parse_type()
        return Param(
            name=name,
            mutable=mutable,
            type_node=type_node,
            loc=SourceLoc.from_token(name_token),
        )

    # ---------- types ----------

    def _parse_type(self) -> TypeNode:
        if self._match(TokenType.KW_I32):
            return I32

        if self._match(TokenType.AMP):
            mutable = self._match(TokenType.KW_MUT)
            inner = self._parse_type()
            return TypeRef(inner=inner, mutable=mutable)

        if self._match(TokenType.LBRACKET):
            inner = self._parse_type()
            self._consume(TokenType.SEMI, "数组类型缺少 ';'，应为 [类型;长度]")
            size_token = self._consume(TokenType.NUM, "数组类型长度应为整数")
            self._consume(TokenType.RBRACKET, "数组类型缺少 ']' ")
            return TypeArray(inner=inner, size=int(size_token.value))

        if self._match(TokenType.LPAREN):
            if self._match(TokenType.RPAREN):
                return TypeTuple(items=tuple())

            first = self._parse_type()
            if self._match(TokenType.COMMA):
                items = [first]
                while not self._check(TokenType.RPAREN):
                    items.append(self._parse_type())
                    if not self._match(TokenType.COMMA):
                        break
                self._consume(TokenType.RPAREN, "元组类型缺少 ')' ")
                return TypeTuple(items=tuple(items))

            self._consume(TokenType.RPAREN, "类型后缺少 ')' ")
            # Parenthesized type for robustness.
            return first

        self._raise_error(self._current(), "无法识别的类型")
        raise ParseError()

    # ---------- blocks ----------

    def _parse_block(self) -> Block:
        lbrace = self._consume(TokenType.LBRACE, "语句块缺少 '{'")
        statements: List[Stmt] = []

        while not self._check(TokenType.RBRACE) and not self._at_end():
            try:
                statements.append(self._parse_statement())
            except ParseError:
                self._synchronize_to_statement()

        self._consume(TokenType.RBRACE, "语句块缺少 '}'")
        return Block(statements=statements, loc=SourceLoc.from_token(lbrace))

    def _parse_flexible_expr_block(self) -> ExprBlock:
        """Parse block that may end with a tail expression.

        Used for function expression blocks and function bodies.
        """
        lbrace = self._consume(TokenType.LBRACE, "函数体缺少 '{'")
        statements: List[Stmt] = []
        tail_expr: Optional[Expr] = None

        non_expr_stmt_heads = {
            TokenType.SEMI,
            TokenType.KW_RETURN,
            TokenType.KW_LET,
            TokenType.KW_WHILE,
            TokenType.KW_FOR,
            TokenType.KW_BREAK,
            TokenType.KW_CONTINUE,
        }

        while not self._check(TokenType.RBRACE) and not self._at_end():
            try:
                cur_type = self._current().token_type

                # Treat if/loop as statements in flexible block to avoid ambiguity.
                if cur_type in non_expr_stmt_heads or cur_type in (TokenType.KW_IF, TokenType.KW_LOOP):
                    statements.append(self._parse_statement())
                    continue

                expr = self._parse_expression()

                if self._match(TokenType.ASSIGN):
                    value = self._parse_expression()
                    self._consume(TokenType.SEMI, "赋值语句缺少 ';'")
                    statements.append(
                        AssignStmt(
                            target=expr,
                            value=value,
                            loc=getattr(expr, "loc", SourceLoc()),
                        )
                    )
                    continue

                if self._match(TokenType.SEMI):
                    statements.append(
                        ExprStmt(expr=expr, loc=getattr(expr, "loc", SourceLoc()))
                    )
                    continue

                tail_expr = expr
                break
            except ParseError:
                self._synchronize_to_statement()

        self._consume(TokenType.RBRACE, "函数体缺少 '}'")
        return ExprBlock(
            statements=statements,
            tail_expr=tail_expr,
            loc=SourceLoc.from_token(lbrace),
        )

    def _parse_expr_block(self) -> ExprBlock:
        """Parse expression block for rule 7.0/7.1/7.3."""
        lbrace = self._consume(TokenType.LBRACE, "表达式块缺少 '{'")
        statements: List[Stmt] = []
        tail_expr: Optional[Expr] = None

        non_expr_stmt_heads = {
            TokenType.SEMI,
            TokenType.KW_RETURN,
            TokenType.KW_LET,
            TokenType.KW_IF,
            TokenType.KW_WHILE,
            TokenType.KW_FOR,
            TokenType.KW_LOOP,
            TokenType.KW_BREAK,
            TokenType.KW_CONTINUE,
        }

        while not self._check(TokenType.RBRACE) and not self._at_end():
            try:
                if self._current().token_type in non_expr_stmt_heads:
                    statements.append(self._parse_statement())
                    continue

                expr = self._parse_expression()

                if self._match(TokenType.ASSIGN):
                    value = self._parse_expression()
                    self._consume(TokenType.SEMI, "赋值语句缺少 ';'")
                    statements.append(
                        AssignStmt(
                            target=expr,
                            value=value,
                            loc=getattr(expr, "loc", SourceLoc()),
                        )
                    )
                    continue

                if self._match(TokenType.SEMI):
                    statements.append(
                        ExprStmt(expr=expr, loc=getattr(expr, "loc", SourceLoc()))
                    )
                    continue

                tail_expr = expr
                break
            except ParseError:
                self._synchronize_to_statement()

        self._consume(TokenType.RBRACE, "表达式块缺少 '}'")
        return ExprBlock(
            statements=statements,
            tail_expr=tail_expr,
            loc=SourceLoc.from_token(lbrace),
        )

    # ---------- statements ----------

    def _parse_statement(self) -> Stmt:
        if self._match(TokenType.SEMI):
            return EmptyStmt(loc=SourceLoc.from_token(self._previous()))

        if self._match(TokenType.KW_RETURN):
            return_token = self._previous()
            if self._match(TokenType.SEMI):
                return ReturnStmt(value=None, loc=SourceLoc.from_token(return_token))
            value = self._parse_expression()
            self._consume(TokenType.SEMI, "return 语句缺少 ';'")
            return ReturnStmt(value=value, loc=SourceLoc.from_token(return_token))

        if self._match(TokenType.KW_LET):
            var_mutable, name, ann, name_loc = self._parse_var_decl()
            init: Optional[Expr] = None
            if self._match(TokenType.ASSIGN):
                init = self._parse_expression()
            self._consume(TokenType.SEMI, "let 语句缺少 ';'")
            return LetStmt(
                name=name,
                mutable=var_mutable,
                annotation=ann,
                init=init,
                loc=name_loc,
            )

        if self._match(TokenType.KW_IF):
            if_token = self._previous()
            return self._parse_if_statement(after_if_consumed=True)

        if self._match(TokenType.KW_WHILE):
            while_token = self._previous()
            cond = self._parse_expression()
            body = self._parse_block()
            return WhileStmt(
                condition=cond,
                body=body,
                loc=SourceLoc.from_token(while_token),
            )

        if self._match(TokenType.KW_FOR):
            for_token = self._previous()
            var_mutable, var_name, var_type, var_loc = self._parse_var_decl()
            self._consume(TokenType.KW_IN, "for 语句缺少 in")
            iterable = self._parse_iterable()
            body = self._parse_block()
            return ForStmt(
                var_name=var_name,
                var_mutable=var_mutable,
                var_type=var_type,
                iterable=iterable,
                body=body,
                loc=var_loc if var_loc.line else SourceLoc.from_token(for_token),
            )

        if self._match(TokenType.KW_LOOP):
            loop_token = self._previous()
            body = self._parse_block()
            return LoopStmt(body=body, loc=SourceLoc.from_token(loop_token))

        if self._match(TokenType.KW_BREAK):
            break_token = self._previous()
            if self._match(TokenType.SEMI):
                return BreakStmt(value=None, loc=SourceLoc.from_token(break_token))
            value = self._parse_expression()
            self._consume(TokenType.SEMI, "break 语句缺少 ';'")
            return BreakStmt(value=value, loc=SourceLoc.from_token(break_token))

        if self._match(TokenType.KW_CONTINUE):
            continue_token = self._previous()
            self._consume(TokenType.SEMI, "continue 语句缺少 ';'")
            return ContinueStmt(loc=SourceLoc.from_token(continue_token))

        expr = self._parse_expression()
        if self._match(TokenType.ASSIGN):
            value = self._parse_expression()
            self._consume(TokenType.SEMI, "赋值语句缺少 ';'")
            return AssignStmt(
                target=expr,
                value=value,
                loc=getattr(expr, "loc", SourceLoc()),
            )

        self._consume(TokenType.SEMI, "表达式语句缺少 ';'")
        return ExprStmt(expr=expr, loc=getattr(expr, "loc", SourceLoc()))

    def _parse_if_statement(self, after_if_consumed: bool = False) -> IfStmt:
        if_token = self._previous() if after_if_consumed else self._current()
        if not after_if_consumed:
            if_token = self._consume(TokenType.KW_IF, "if 语句应以 if 开始")

        cond = self._parse_expression()
        then_block = self._parse_block()
        else_branch: Optional[Union[IfStmt, Block]] = None

        if self._match(TokenType.KW_ELSE):
            if self._match(TokenType.KW_IF):
                else_branch = self._parse_if_statement(after_if_consumed=True)
            else:
                else_branch = self._parse_block()

        return IfStmt(
            condition=cond,
            then_block=then_block,
            else_branch=else_branch,
            loc=SourceLoc.from_token(if_token),
        )

    def _parse_var_decl(self) -> Tuple[bool, str, Optional[TypeNode], SourceLoc]:
        var_mutable = self._match(TokenType.KW_MUT)
        name_token = self._consume(TokenType.IDENT, "变量声明缺少标识符")
        name = name_token.value
        annotation: Optional[TypeNode] = None
        if self._match(TokenType.COLON):
            annotation = self._parse_type()
        return var_mutable, name, annotation, SourceLoc.from_token(name_token)

    def _parse_iterable(self) -> Expr:
        start = self._parse_expression()
        if self._match(TokenType.DOTDOT):
            range_token = self._previous()
            end = self._parse_expression()
            return RangeExpr(start=start, end=end, loc=SourceLoc.from_token(range_token))
        return start

    # ---------- expressions ----------

    def _parse_expression(self) -> Expr:
        return self._parse_comparison()

    def _parse_comparison(self) -> Expr:
        expr = self._parse_additive()
        while self._match(
            TokenType.LT,
            TokenType.LE,
            TokenType.GT,
            TokenType.GE,
            TokenType.EQ,
            TokenType.NEQ,
        ):
            op_token = self._previous()
            op = op_token.value
            right = self._parse_additive()
            expr = BinaryExpr(
                op=op,
                left=expr,
                right=right,
                loc=SourceLoc.from_token(op_token),
            )
        return expr

    def _parse_additive(self) -> Expr:
        expr = self._parse_multiplicative()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            op_token = self._previous()
            op = op_token.value
            right = self._parse_multiplicative()
            expr = BinaryExpr(
                op=op,
                left=expr,
                right=right,
                loc=SourceLoc.from_token(op_token),
            )
        return expr

    def _parse_multiplicative(self) -> Expr:
        expr = self._parse_unary()
        while self._match(TokenType.STAR, TokenType.SLASH):
            op_token = self._previous()
            op = op_token.value
            right = self._parse_unary()
            expr = BinaryExpr(
                op=op,
                left=expr,
                right=right,
                loc=SourceLoc.from_token(op_token),
            )
        return expr

    def _parse_unary(self) -> Expr:
        if self._match(TokenType.AMP):
            amp_token = self._previous()
            if self._match(TokenType.KW_MUT):
                operand = self._parse_unary()
                return UnaryExpr(op="&mut", operand=operand, loc=SourceLoc.from_token(amp_token))
            operand = self._parse_unary()
            return UnaryExpr(op="&", operand=operand, loc=SourceLoc.from_token(amp_token))

        if self._match(TokenType.STAR):
            star_token = self._previous()
            operand = self._parse_unary()
            return UnaryExpr(op="*", operand=operand, loc=SourceLoc.from_token(star_token))

        return self._parse_postfix()

    def _parse_postfix(self) -> Expr:
        expr = self._parse_primary()

        while True:
            if self._match(TokenType.LPAREN):
                lparen = self._previous()
                args: List[Expr] = []
                if not self._check(TokenType.RPAREN):
                    while True:
                        args.append(self._parse_expression())
                        if not self._match(TokenType.COMMA):
                            break
                self._consume(TokenType.RPAREN, "函数调用缺少 ')' ")
                expr = CallExpr(callee=expr, args=args, loc=SourceLoc.from_token(lparen))
                continue

            if self._match(TokenType.LBRACKET):
                lbracket = self._previous()
                idx = self._parse_expression()
                self._consume(TokenType.RBRACKET, "下标访问缺少 ']' ")
                expr = IndexExpr(base=expr, index=idx, loc=SourceLoc.from_token(lbracket))
                continue

            if self._match(TokenType.DOT):
                dot_token = self._previous()
                index_tok = self._consume(TokenType.NUM, "元组点访问应为 '.<NUM>'")
                expr = FieldExpr(
                    base=expr,
                    index=int(index_tok.value),
                    loc=SourceLoc.from_token(dot_token),
                )
                continue

            break

        return expr

    def _parse_primary(self) -> Expr:
        if self._match(TokenType.NUM):
            token = self._previous()
            return NumExpr(value=int(token.value), loc=SourceLoc.from_token(token))

        if self._match(TokenType.IDENT):
            token = self._previous()
            return IdentExpr(name=token.value, loc=SourceLoc.from_token(token))

        if self._match(TokenType.KW_IF):
            if_token = self._previous()
            cond = self._parse_expression()
            then_block = self._parse_expr_block()
            self._consume(TokenType.KW_ELSE, "if 表达式必须包含 else 分支")
            else_block = self._parse_expr_block()
            return IfExpr(
                condition=cond,
                then_block=then_block,
                else_block=else_block,
                loc=SourceLoc.from_token(if_token),
            )

        if self._match(TokenType.KW_LOOP):
            loop_token = self._previous()
            body = self._parse_block()
            return LoopExpr(body=body, loc=SourceLoc.from_token(loop_token))

        if self._match(TokenType.LBRACE):
            lbrace = self._previous()
            # put back one token and call shared parser
            self.index -= 1
            return BlockExpr(
                block=self._parse_expr_block(),
                loc=SourceLoc.from_token(lbrace),
            )

        if self._match(TokenType.LBRACKET):
            lbracket = self._previous()
            elements: List[Expr] = []
            if not self._check(TokenType.RBRACKET):
                while True:
                    elements.append(self._parse_expression())
                    if not self._match(TokenType.COMMA):
                        break
            self._consume(TokenType.RBRACKET, "数组字面量缺少 ']' ")
            return ArrayExpr(elements=elements, loc=SourceLoc.from_token(lbracket))

        if self._match(TokenType.LPAREN):
            lparen = self._previous()
            if self._match(TokenType.RPAREN):
                return TupleExpr(elements=[], loc=SourceLoc.from_token(lparen))

            first = self._parse_expression()
            if self._match(TokenType.COMMA):
                elements = [first]
                while not self._check(TokenType.RPAREN):
                    elements.append(self._parse_expression())
                    if not self._match(TokenType.COMMA):
                        break
                self._consume(TokenType.RPAREN, "元组表达式缺少 ')' ")
                return TupleExpr(elements=elements, loc=SourceLoc.from_token(lparen))

            self._consume(TokenType.RPAREN, "分组表达式缺少 ')' ")
            return first

        self._raise_error(self._current(), "无法识别的表达式起始符")
        raise ParseError()


# ==================== Utility output ====================


def format_ast_summary(program: Program) -> str:
    lines = ["=== AST Summary ==="]
    lines.append(f"functions: {len(program.functions)}")
    for fn in program.functions:
        ret = "(no return type)" if fn.return_type is None else "has return type"
        lines.append(
            f"- fn {fn.name}: params={len(fn.params)}, stmts={len(fn.body.statements)}, "
            f"tail_expr={'yes' if fn.body.tail_expr is not None else 'no'}, {ret}"
        )
    return "\n".join(lines)


def _ast_to_obj(node):
    """Convert AST node graph into plain Python objects for JSON/tree rendering."""
    if node is None:
        return None

    if isinstance(node, (str, int, float, bool)):
        return node

    if isinstance(node, list):
        return [_ast_to_obj(x) for x in node]

    if isinstance(node, tuple):
        return [_ast_to_obj(x) for x in node]

    if is_dataclass(node):
        result = {"kind": type(node).__name__}
        for f in dataclass_fields(node):
            result[f.name] = _ast_to_obj(getattr(node, f.name))
        return result

    return str(node)


def program_to_dict(program: Program) -> Dict[str, Any]:
    obj = _ast_to_obj(program)
    if isinstance(obj, dict):
        return obj
    # Defensive fallback; Program should always serialize to a dict.
    return {"kind": "Program", "value": str(obj)}


def format_ast_json(program: Program) -> str:
    return json.dumps(program_to_dict(program), ensure_ascii=False, indent=2)


def _render_tree(lines: List[str], value, prefix: str, name: str) -> None:
    """Render a dict/list scalar recursively as a tree-like text."""
    label = f"{prefix}{name}:"
    if isinstance(value, dict):
        kind = value.get("kind")
        if kind is not None:
            lines.append(f"{label} {kind}")
        else:
            lines.append(label)
        for k, v in value.items():
            if k == "kind":
                continue
            _render_tree(lines, v, prefix + "  ", k)
        return

    if isinstance(value, list):
        lines.append(f"{label} [{len(value)}]")
        for i, item in enumerate(value):
            _render_tree(lines, item, prefix + "  ", f"[{i}]")
        return

    lines.append(f"{label} {value}")


def format_ast_tree(program: Program) -> str:
    root = program_to_dict(program)
    lines: List[str] = ["=== AST Tree ==="]
    _render_tree(lines, root, "", "Program")
    return "\n".join(lines)


# ==================== CLI ====================


def main() -> None:
    # 确保在 Windows 控制台/管道下中文诊断信息按 UTF-8 输出，避免乱码。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    argp = argparse.ArgumentParser(description="Class-Rust parser and checker")
    argp.add_argument("path", help="source file path")
    argp.add_argument(
        "--mode",
        choices=["parse", "check"],
        default="check",
        help="parse: print AST summary; check: run semantic checks",
    )
    argp.add_argument(
        "--ast-format",
        choices=["summary", "tree", "json"],
        default="summary",
        help="how to print AST analysis result",
    )
    argp.add_argument(
        "--ast-out",
        default=None,
        help="optional output file path for AST text/json",
    )
    args = argp.parse_args()

    with open(args.path, "r", encoding="utf-8") as f:
        source = f.read()

    lexer = Lexer(source)
    tokens = lexer.tokenize()

    if lexer.errors:
        print("=== Lex Errors ===")
        for e in lexer.errors:
            print(e)

    parser = Parser(tokens)
    program = parser.parse()

    if parser.errors:
        print("=== Parse Errors ===")
        for e in parser.errors:
            print(e)
    else:
        if args.ast_format == "summary":
            ast_output = format_ast_summary(program)
        elif args.ast_format == "tree":
            ast_output = format_ast_tree(program)
        else:
            ast_output = format_ast_json(program)

        print(ast_output)
        if args.ast_out:
            with open(args.ast_out, "w", encoding="utf-8") as f:
                f.write(ast_output)
            print(f"=== AST output written: {args.ast_out} ===")

    if args.mode == "check":
        # 语义检查与中间代码生成统一由 semantic.py 提供（此处惰性导入避免循环依赖）。
        from semantic import SemanticAnalyzer

        checker = SemanticAnalyzer()
        sem_errors = checker.check(program)
        if sem_errors:
            print("=== Semantic Errors ===")
            for e in sem_errors:
                print(e)
        else:
            print("=== Semantic Check Passed ===")


if __name__ == "__main__":
    # 通过模块形式再分发，确保 parser 与 semantic 引用同一套 AST 类。
    # 否则 `python parser.py` 时，本文件作为 __main__ 与被 semantic 导入的
    # parser 模块各持有一份 AST 类，isinstance 全部失配，语义检查会静默放过。
    from parser import main as _module_main

    _module_main()
