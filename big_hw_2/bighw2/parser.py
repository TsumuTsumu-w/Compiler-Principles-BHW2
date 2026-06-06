"""Class-Rust parser and semantic checker for assignment 1.

This module builds on lexer.py and implements:
1) Recursive-descent parser for grammar rules 0.1~9.3 in the handout.
2) Basic semantic checks, including the three "entanglement" points on page 20.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields as dataclass_fields, is_dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import argparse
import json

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


# ==================== Semantic checking ====================


@dataclass
class VarInfo:
    mutable: bool
    type_node: TypeNode


class SemanticChecker:
    def __init__(self):
        self.errors: List[str] = []
        self.diagnostics: List[Diagnostic] = []
        self.scopes: List[Dict[str, VarInfo]] = []
        self.current_return_type: Optional[TypeNode] = None
        self.loop_break_types: List[List[TypeNode]] = []

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

    def check(self, program: Program) -> List[str]:
        for fn in program.functions:
            self._check_function(fn)
        return self.errors

    def _check_function(self, fn: FunctionDecl) -> None:
        self._push_scope()
        for p in fn.params:
            self._declare(
                p.name,
                VarInfo(mutable=p.mutable, type_node=p.type_node),
                p.loc,
            )

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
            self._declare(
                stmt.name,
                VarInfo(mutable=stmt.mutable, type_node=final_type),
                stmt.loc,
            )
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
                    self._report(
                        "for 循环仅允许遍历区间表达式或数组表达式",
                        stmt.iterable.loc,
                    )

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
            self._declare(
                stmt.var_name,
                VarInfo(mutable=stmt.var_mutable, type_node=loop_var_type),
                stmt.loc,
            )
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
            # Function signature table can be added later.
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
        checker = SemanticChecker()
        sem_errors = checker.check(program)
        if sem_errors:
            print("=== Semantic Errors ===")
            for e in sem_errors:
                print(e)
        else:
            print("=== Semantic Check Passed ===")


if __name__ == "__main__":
    main()
