"""
类 Rust 词法分析器
同济大学 编译原理 大作业1

核心原理：
  将源代码视为字符流，用一个指针 pos 从头到尾扫描。
  每次调用 next_token() 时，根据当前字符决定进入哪个"状态分支"：
    - 字母/下划线 → 识别 标识符 或 关键字
    - 数字         → 识别 数值
    - 运算符字符   → 识别 单字符或双字符运算符
    - ...
  这本质上就是一个 DFA（确定有限自动机）的手工实现。
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List


# ==================== Token 类型定义 ====================

class TokenType(Enum):
    # 关键字
    KW_I32      = auto()
    KW_LET      = auto()
    KW_IF       = auto()
    KW_ELSE     = auto()
    KW_WHILE    = auto()
    KW_RETURN   = auto()
    KW_MUT      = auto()
    KW_FN       = auto()
    KW_FOR      = auto()
    KW_IN       = auto()
    KW_LOOP     = auto()
    KW_BREAK    = auto()
    KW_CONTINUE = auto()

    # 标识符和数值
    IDENT  = auto()  # 标识符
    NUM    = auto()  # 整数数值

    # 赋值号
    ASSIGN = auto()  # =

    # 算术运算符
    PLUS   = auto()  # +
    MINUS  = auto()  # -
    STAR   = auto()  # *
    SLASH  = auto()  # /

    # 比较运算符
    EQ     = auto()  # ==
    NEQ    = auto()  # !=
    GT     = auto()  # >
    GE     = auto()  # >=
    LT     = auto()  # <
    LE     = auto()  # <=

    # 逻辑/位运算符
    AMP    = auto()  # &

    # 界符
    LPAREN   = auto()  # (
    RPAREN   = auto()  # )
    LBRACE   = auto()  # {
    RBRACE   = auto()  # }
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]

    # 分隔符
    SEMI   = auto()  # ;
    COLON  = auto()  # :
    COMMA  = auto()  # ,

    # 特殊符号
    ARROW  = auto()  # ->
    DOT    = auto()  # .
    DOTDOT = auto()  # ..

    # 结束符
    EOF    = auto()  # 文件末尾 / #
    HASH   = auto()  # # (结束符)

    # 错误
    ERROR  = auto()


# 关键字映射表：字符串 → TokenType
KEYWORDS = {
    "i32":      TokenType.KW_I32,
    "let":      TokenType.KW_LET,
    "if":       TokenType.KW_IF,
    "else":     TokenType.KW_ELSE,
    "while":    TokenType.KW_WHILE,
    "return":   TokenType.KW_RETURN,
    "mut":      TokenType.KW_MUT,
    "fn":       TokenType.KW_FN,
    "for":      TokenType.KW_FOR,
    "in":       TokenType.KW_IN,
    "loop":     TokenType.KW_LOOP,
    "break":    TokenType.KW_BREAK,
    "continue": TokenType.KW_CONTINUE,
}


@dataclass
class Token:
    token_type: TokenType
    value: str        # 原始文本
    line: int         # 所在行号
    column: int       # 所在列号

    def __repr__(self):
        type_name = self.token_type.name
        if self.token_type in (TokenType.IDENT, TokenType.NUM, TokenType.ERROR):
            return f"({type_name}, \"{self.value}\", Ln {self.line}:{self.column})"
        elif self.token_type.name.startswith("KW_"):
            return f"(关键字, \"{self.value}\", Ln {self.line}:{self.column})"
        else:
            return f"({type_name}, \"{self.value}\", Ln {self.line}:{self.column})"


# ==================== 词法分析器 ====================

class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0            # 当前字符位置（全局偏移）
        self.line = 1           # 当前行号
        self.column = 1         # 当前列号
        self.errors: List[str] = []

    # ---------- 字符级辅助方法 ----------

    def _current_char(self) -> str:
        """返回当前字符，到末尾返回 '\\0'"""
        if self.pos >= len(self.source):
            return '\0'
        return self.source[self.pos]

    def _peek_char(self) -> str:
        """返回下一个字符（不移动指针），到末尾返回 '\\0'"""
        if self.pos + 1 >= len(self.source):
            return '\0'
        return self.source[self.pos + 1]

    def _advance(self) -> str:
        """消耗当前字符并前进，返回被消耗的字符"""
        ch = self._current_char()
        if ch == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        self.pos += 1
        return ch

    def _make_token(self, token_type: TokenType, value: str, line: int, col: int) -> Token:
        return Token(token_type, value, line, col)

    def _error_token(self, msg: str, value: str, line: int, col: int) -> Token:
        self.errors.append(f"Ln {line}:{col} 词法错误: {msg}")
        return Token(TokenType.ERROR, value, line, col)

    # ---------- 跳过空白和注释 ----------

    def _skip_whitespace_and_comments(self):
        """
        这里体现了自动机的思想：
        遇到空白 → 跳过
        遇到 // → 跳过到行尾
        遇到 /* → 跳过到 */ 结束
        循环直到当前字符既不是空白也不是注释开头
        """
        while self.pos < len(self.source):
            ch = self._current_char()

            # 空白字符：直接跳过
            if ch in (' ', '\t', '\r', '\n'):
                self._advance()
                continue

            # 单行注释 //
            if ch == '/' and self._peek_char() == '/':
                self._advance()  # 跳过第一个 /
                self._advance()  # 跳过第二个 /
                while self._current_char() != '\n' and self._current_char() != '\0':
                    self._advance()
                continue

            # 多行注释 /* ... */
            if ch == '/' and self._peek_char() == '*':
                start_line, start_col = self.line, self.column
                self._advance()  # 跳过 /
                self._advance()  # 跳过 *
                depth = 1
                while depth > 0 and self._current_char() != '\0':
                    if self._current_char() == '/' and self._peek_char() == '*':
                        depth += 1
                        self._advance()
                        self._advance()
                    elif self._current_char() == '*' and self._peek_char() == '/':
                        depth -= 1
                        self._advance()
                        self._advance()
                    else:
                        self._advance()
                if depth > 0:
                    self.errors.append(f"Ln {start_line}:{start_col} 词法错误: 未闭合的多行注释")
                continue

            break  # 不是空白也不是注释，退出

    # ---------- 识别各类 Token 的子自动机 ----------

    def _read_identifier_or_keyword(self) -> Token:
        """
        标识符/关键字 DFA:
          状态0(初始): 遇到 字母|_ → 进入状态1
          状态1(接受): 遇到 字母|数字|_ → 保持状态1；否则 → 结束
        识别完成后查关键字表，决定是关键字还是标识符。
        """
        start_line, start_col = self.line, self.column
        start = self.pos

        while self._current_char().isalnum() or self._current_char() == '_':
            self._advance()

        text = self.source[start:self.pos]
        token_type = KEYWORDS.get(text, TokenType.IDENT)
        return self._make_token(token_type, text, start_line, start_col)

    def _read_number(self) -> Token:
        """
        数值 DFA:
          状态0(初始): 遇到数字 → 进入状态1
          状态1(接受): 遇到数字 → 保持状态1；否则 → 结束
        """
        start_line, start_col = self.line, self.column
        start = self.pos

        while self._current_char().isdigit():
            self._advance()

        # 如果数字后面紧跟字母或下划线，说明是非法 token（如 123abc）
        if self._current_char().isalpha() or self._current_char() == '_':
            while self._current_char().isalnum() or self._current_char() == '_':
                self._advance()
            text = self.source[start:self.pos]
            return self._error_token(f"非法标识符 \"{text}\"（数字不能作为标识符开头）", text, start_line, start_col)

        text = self.source[start:self.pos]
        return self._make_token(TokenType.NUM, text, start_line, start_col)

    # ---------- 核心：获取下一个 Token ----------

    def next_token(self) -> Token:
        """
        DFA 主入口：根据当前字符决定进入哪个分支。
        这就是你说的"自动机跳转"的核心逻辑。
        """
        self._skip_whitespace_and_comments()

        if self.pos >= len(self.source):
            return self._make_token(TokenType.EOF, "", self.line, self.column)

        ch = self._current_char()
        line, col = self.line, self.column

        # ---- 标识符 / 关键字 ----
        if ch.isalpha() or ch == '_':
            return self._read_identifier_or_keyword()

        # ---- 数值 ----
        if ch.isdigit():
            return self._read_number()

        # ---- 双字符优先判断的运算符和特殊符号 ----

        # = 或 ==
        if ch == '=':
            self._advance()
            if self._current_char() == '=':
                self._advance()
                return self._make_token(TokenType.EQ, "==", line, col)
            return self._make_token(TokenType.ASSIGN, "=", line, col)

        # ! 只可能是 !=
        if ch == '!':
            self._advance()
            if self._current_char() == '=':
                self._advance()
                return self._make_token(TokenType.NEQ, "!=", line, col)
            return self._error_token("未预期的字符 '!'（你是否想输入 '!='？）", "!", line, col)

        # > 或 >=
        if ch == '>':
            self._advance()
            if self._current_char() == '=':
                self._advance()
                return self._make_token(TokenType.GE, ">=", line, col)
            return self._make_token(TokenType.GT, ">", line, col)

        # < 或 <=
        if ch == '<':
            self._advance()
            if self._current_char() == '=':
                self._advance()
                return self._make_token(TokenType.LE, "<=", line, col)
            return self._make_token(TokenType.LT, "<", line, col)

        # - 或 ->
        if ch == '-':
            self._advance()
            if self._current_char() == '>':
                self._advance()
                return self._make_token(TokenType.ARROW, "->", line, col)
            return self._make_token(TokenType.MINUS, "-", line, col)

        # . 或 ..
        if ch == '.':
            self._advance()
            if self._current_char() == '.':
                self._advance()
                return self._make_token(TokenType.DOTDOT, "..", line, col)
            return self._make_token(TokenType.DOT, ".", line, col)

        # / （前面已经排除了注释的情况）
        if ch == '/':
            self._advance()
            return self._make_token(TokenType.SLASH, "/", line, col)

        # ---- 单字符 Token（直接查表） ----
        SINGLE_CHAR_TOKENS = {
            '+': TokenType.PLUS,
            '*': TokenType.STAR,
            '&': TokenType.AMP,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
            '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET,
            ';': TokenType.SEMI,
            ':': TokenType.COLON,
            ',': TokenType.COMMA,
            '#': TokenType.HASH,
        }

        if ch in SINGLE_CHAR_TOKENS:
            self._advance()
            return self._make_token(SINGLE_CHAR_TOKENS[ch], ch, line, col)

        # ---- 无法识别的字符 ----
        self._advance()
        return self._error_token(f"无法识别的字符 '{ch}'", ch, line, col)

    # ---------- 一次性分析所有 Token ----------

    def tokenize(self) -> List[Token]:
        tokens = []
        while True:
            token = self.next_token()
            tokens.append(token)
            if token.token_type in (TokenType.EOF, TokenType.HASH):
                break
        return tokens


# ==================== 格式化输出 ====================

def format_token_table(tokens: List[Token]) -> str:
    """将 Token 列表格式化为表格形式"""
    lines = []
    lines.append(f"{'序号':>4}  {'类型':<14}  {'值':<16}  {'位置':<10}")
    lines.append("-" * 52)
    for i, tok in enumerate(tokens, 1):
        type_name = tok.token_type.name
        if type_name.startswith("KW_"):
            category = f"关键字"
        elif type_name == "IDENT":
            category = "标识符"
        elif type_name == "NUM":
            category = "整数"
        elif type_name == "ERROR":
            category = "!! 错误"
        else:
            category = type_name
        pos = f"Ln {tok.line}:{tok.column}"
        lines.append(f"{i:>4}  {category:<12}  {tok.value:<16}  {pos:<10}")
    return "\n".join(lines)


# ==================== 主程序 ====================

def main():
    import sys

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        print(f"=== 词法分析: {filepath} ===\n")
    else:
        source = """
fn program_1_5() -> i32 {
    return 1;
}

fn program_2_3() {
    let mut a = 1;
    let mut b: i32 = 1;
}

fn program_3_4() {
    1 * 2;
    3 / 4;
}

fn program_4_1(a: i32) -> i32 {
    if a > 0 {
        return 1;
    }
}

fn program_5_1(mut n: i32) {
    while n > 0 {
        n = n - 1;
    }
}
""".strip()
        print("=== 词法分析: 内置示例 ===\n")
        print("--- 源代码 ---")
        for i, line in enumerate(source.split('\n'), 1):
            print(f"  {i:>3} | {line}")
        print()

    lexer = Lexer(source)
    tokens = lexer.tokenize()

    print("--- Token 序列 ---")
    print(format_token_table(tokens))
    print(f"\n共识别 {len(tokens)} 个 Token")

    if lexer.errors:
        print(f"\n--- 错误信息 ({len(lexer.errors)} 个) ---")
        for err in lexer.errors:
            print(f"  {err}")


if __name__ == "__main__":
    main()
