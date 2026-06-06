"""词法分析器测试"""
from lexer import Lexer, TokenType


def _check(name, source, expected_types):
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    actual = [(t.token_type, t.value) for t in tokens if t.token_type != TokenType.EOF]
    ok = all(a[0] == e for a, e in zip(actual, expected_types)) and len(actual) == len(expected_types)
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}")
    if not ok:
        print(f"  source:   {source!r}")
        print(f"  expected: {[t.name for t in expected_types]}")
        print(f"  actual:   {[(t.name, v) for t, v in actual]}")
    return ok


def _check_errors(name, source, expected_error_count):
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    actual_errors = len(lexer.errors)
    ok = actual_errors == expected_error_count
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}")
    if not ok:
        print(f"  source:        {source!r}")
        print(f"  expected errs: {expected_error_count}")
        print(f"  actual errs:   {actual_errors}")
        for e in lexer.errors:
            print(f"    {e}")
    return ok


def _check_line_col(name, source, expected_positions):
    """Check that tokens have the expected (line, column) positions."""
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    actual = [(t.token_type, t.line, t.column) for t in tokens if t.token_type != TokenType.EOF]
    ok = len(actual) == len(expected_positions)
    if ok:
        for (atype, al, ac), (etype, el, ec) in zip(actual, expected_positions):
            if atype != etype or al != el or ac != ec:
                ok = False
                break
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}")
    if not ok:
        print(f"  expected: {[(t[0].name, t[1], t[2]) for t in expected_positions]}")
        print(f"  actual:   {[(t[0].name, t[1], t[2]) for t in actual]}")
    return ok


_passed = 0
_total = 0

def _run(name, source, expected):
    global _passed, _total
    _total += 1
    if _check(name, source, expected):
        _passed += 1

def _run_errors(name, source, expected_error_count):
    global _passed, _total
    _total += 1
    if _check_errors(name, source, expected_error_count):
        _passed += 1

def _run_line_col(name, source, expected_positions):
    global _passed, _total
    _total += 1
    if _check_line_col(name, source, expected_positions):
        _passed += 1


# ================================================================
# 1. 基本 Token 识别
# ================================================================

_run("if123 is identifier",
    "if123",
    [TokenType.IDENT])

_run("if=123 is three tokens",
    "if=123",
    [TokenType.KW_IF, TokenType.ASSIGN, TokenType.NUM])

_run("all keywords",
    "i32 let if else while return mut fn for in loop break continue",
    [TokenType.KW_I32, TokenType.KW_LET, TokenType.KW_IF, TokenType.KW_ELSE,
     TokenType.KW_WHILE, TokenType.KW_RETURN, TokenType.KW_MUT, TokenType.KW_FN,
     TokenType.KW_FOR, TokenType.KW_IN, TokenType.KW_LOOP, TokenType.KW_BREAK,
     TokenType.KW_CONTINUE])

_run("comparison operators",
    "== != > >= < <=",
    [TokenType.EQ, TokenType.NEQ, TokenType.GT, TokenType.GE, TokenType.LT, TokenType.LE])

_run("arithmetic operators",
    "+ - * /",
    [TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH])

_run("arrow and dots",
    "-> . ..",
    [TokenType.ARROW, TokenType.DOT, TokenType.DOTDOT])

_run("all delimiters",
    "( ) { } [ ]",
    [TokenType.LPAREN, TokenType.RPAREN, TokenType.LBRACE, TokenType.RBRACE,
     TokenType.LBRACKET, TokenType.RBRACKET])

_run("separators",
    "; : ,",
    [TokenType.SEMI, TokenType.COLON, TokenType.COMMA])

_run("single line comment",
    "a // this is comment\nb",
    [TokenType.IDENT, TokenType.IDENT])

_run("multi line comment",
    "a /* comment\nmore */ b",
    [TokenType.IDENT, TokenType.IDENT])

_run("fn program_1_5() -> i32 { return 1; }",
    "fn program_1_5() -> i32 { return 1; }",
    [TokenType.KW_FN, TokenType.IDENT, TokenType.LPAREN, TokenType.RPAREN,
     TokenType.ARROW, TokenType.KW_I32, TokenType.LBRACE,
     TokenType.KW_RETURN, TokenType.NUM, TokenType.SEMI, TokenType.RBRACE])

_run("for loop with ..",
    "for mut i in 1..n+1 { }",
    [TokenType.KW_FOR, TokenType.KW_MUT, TokenType.IDENT, TokenType.KW_IN,
     TokenType.NUM, TokenType.DOTDOT, TokenType.IDENT, TokenType.PLUS, TokenType.NUM,
     TokenType.LBRACE, TokenType.RBRACE])

_run("reference & and &mut",
    "& a &mut b *c",
    [TokenType.AMP, TokenType.IDENT, TokenType.AMP, TokenType.KW_MUT,
     TokenType.IDENT, TokenType.STAR, TokenType.IDENT])

_run("hash end marker",
    "a #",
    [TokenType.IDENT, TokenType.HASH])

_run("underscore identifiers",
    "_foo _123 __bar",
    [TokenType.IDENT, TokenType.IDENT, TokenType.IDENT])

_run("error: 123abc",
    "123abc",
    [TokenType.ERROR])


# ================================================================
# 2. 边界与空白处理
# ================================================================

_run("empty input produces only EOF",
    "",
    [])

_run("whitespace only produces only EOF",
    "   \t\n\r  ",
    [])

_run("single identifier",
    "x",
    [TokenType.IDENT])

_run("single number",
    "42",
    [TokenType.NUM])

_run("zero literal",
    "0",
    [TokenType.NUM])

_run("large number",
    "999999",
    [TokenType.NUM])

_run("tokens separated by various whitespace",
    "a\t\n b",
    [TokenType.IDENT, TokenType.IDENT])


# ================================================================
# 3. 注释边界情况
# ================================================================

_run("comment at end of input without newline",
    "a // comment",
    [TokenType.IDENT])

_run("empty single-line comment",
    "a //\nb",
    [TokenType.IDENT, TokenType.IDENT])

_run("empty multi-line comment",
    "a /**/ b",
    [TokenType.IDENT, TokenType.IDENT])

_run("nested multi-line comments",
    "a /* outer /* inner */ still_outer */ b",
    [TokenType.IDENT, TokenType.IDENT])

_run("multi-line comment spanning many lines",
    "a /* line1\nline2\nline3\nline4 */ b",
    [TokenType.IDENT, TokenType.IDENT])

_run("comment between tokens",
    "a/* comment */b",
    [TokenType.IDENT, TokenType.IDENT])

_run("division after comment",
    "a /*c*/ / b",
    [TokenType.IDENT, TokenType.SLASH, TokenType.IDENT])


# ================================================================
# 4. 运算符紧邻标识符（无空格）
# ================================================================

_run("no space between identifier and operator",
    "a+b",
    [TokenType.IDENT, TokenType.PLUS, TokenType.IDENT])

_run("no space around assignment",
    "a=1",
    [TokenType.IDENT, TokenType.ASSIGN, TokenType.NUM])

_run("no space around comparison",
    "a==b",
    [TokenType.IDENT, TokenType.EQ, TokenType.IDENT])

_run("no space around arrow",
    "->",
    [TokenType.ARROW])

_run("minus vs arrow",
    "- >",
    [TokenType.MINUS, TokenType.GT])

_run("dot vs dotdot",
    ". ..",
    [TokenType.DOT, TokenType.DOTDOT])

_run("dotdot no space",
    "1..2",
    [TokenType.NUM, TokenType.DOTDOT, TokenType.NUM])

_run("not-equal no space",
    "a!=b",
    [TokenType.IDENT, TokenType.NEQ, TokenType.IDENT])

_run("greater-equal no space",
    "a>=b",
    [TokenType.IDENT, TokenType.GE, TokenType.IDENT])

_run("less-equal no space",
    "a<=b",
    [TokenType.IDENT, TokenType.LE, TokenType.IDENT])


# ================================================================
# 5. 词法错误
# ================================================================

_run_errors("bare ! is error", "!", 1)
_run_errors("bare @ is error", "@", 1)
_run_errors("bare # is not error (it's HASH)", "#", 0)
_run_errors("unclosed multi-line comment", "a /* unclosed", 1)
_run_errors("deeply nested unclosed comment", "a /* /* /* unclosed", 1)
_run_errors("number followed by letters", "123abc", 1)
_run_errors("number followed by underscore", "123_abc", 1)
_run_errors("multiple errors in one input", "! @ 123abc", 3)
_run_errors("no errors for valid input", "fn main() { let x:i32 = 1; }", 0)
_run_errors("no errors for empty input", "", 0)


# ================================================================
# 6. 行号列号追踪
# ================================================================

_run_line_col("single token position",
    "abc",
    [(TokenType.IDENT, 1, 1)])

_run_line_col("second token position",
    "abc def",
    [(TokenType.IDENT, 1, 1), (TokenType.IDENT, 1, 5)])

_run_line_col("token on second line",
    "abc\ndef",
    [(TokenType.IDENT, 1, 1), (TokenType.IDENT, 2, 1)])

_run_line_col("column after operator",
    "a+b",
    [(TokenType.IDENT, 1, 1), (TokenType.PLUS, 1, 2), (TokenType.IDENT, 1, 3)])

_run_line_col("position after comment",
    "a // comment\nb",
    [(TokenType.IDENT, 1, 1), (TokenType.IDENT, 2, 1)])


# ================================================================
# 7. 关键字边界
# ================================================================

_run("keyword prefix of longer identifier",
    "iff",
    [TokenType.IDENT])

_run("keyword as part of identifier",
    "while_loop",
    [TokenType.IDENT])

_run("keyword let",
    "let",
    [TokenType.KW_LET])

_run("keyword loop",
    "loop",
    [TokenType.KW_LOOP])

_run("keyword break",
    "break",
    [TokenType.KW_BREAK])

_run("keyword continue",
    "continue",
    [TokenType.KW_CONTINUE])

_run("keyword return",
    "return",
    [TokenType.KW_RETURN])

_run("keyword fn",
    "fn",
    [TokenType.KW_FN])

_run("keyword for",
    "for",
    [TokenType.KW_FOR])

_run("keyword in",
    "in",
    [TokenType.KW_IN])

_run("keyword mut",
    "mut",
    [TokenType.KW_MUT])

_run("keyword i32",
    "i32",
    [TokenType.KW_I32])


# ================================================================
# 8. 复杂组合
# ================================================================

_run("full function with types and body",
    "fn add(mut a:i32,mut b:i32)->i32{a+b}",
    [TokenType.KW_FN, TokenType.IDENT, TokenType.LPAREN,
     TokenType.KW_MUT, TokenType.IDENT, TokenType.COLON, TokenType.KW_I32, TokenType.COMMA,
     TokenType.KW_MUT, TokenType.IDENT, TokenType.COLON, TokenType.KW_I32, TokenType.RPAREN,
     TokenType.ARROW, TokenType.KW_I32, TokenType.LBRACE,
     TokenType.IDENT, TokenType.PLUS, TokenType.IDENT, TokenType.RBRACE])

_run("array literal",
    "[1, 2, 3]",
    [TokenType.LBRACKET, TokenType.NUM, TokenType.COMMA, TokenType.NUM,
     TokenType.COMMA, TokenType.NUM, TokenType.RBRACKET])

_run("tuple expression",
    "(1, 2)",
    [TokenType.LPAREN, TokenType.NUM, TokenType.COMMA, TokenType.NUM, TokenType.RPAREN])

_run("nested braces",
    "{ { } }",
    [TokenType.LBRACE, TokenType.LBRACE, TokenType.RBRACE, TokenType.RBRACE])

_run("mixed operators precedence tokens",
    "a+b*c-d/e",
    [TokenType.IDENT, TokenType.PLUS, TokenType.IDENT, TokenType.STAR,
     TokenType.IDENT, TokenType.MINUS, TokenType.IDENT, TokenType.SLASH, TokenType.IDENT])

_run("reference type annotation",
    "& i32",
    [TokenType.AMP, TokenType.KW_I32])

_run("mutable reference type annotation",
    "&mut i32",
    [TokenType.AMP, TokenType.KW_MUT, TokenType.KW_I32])

_run("dereference expression",
    "*a",
    [TokenType.STAR, TokenType.IDENT])

_run("index access",
    "a[0]",
    [TokenType.IDENT, TokenType.LBRACKET, TokenType.NUM, TokenType.RBRACKET])

_run("tuple field access",
    "a.0",
    [TokenType.IDENT, TokenType.DOT, TokenType.NUM])

_run("range in for loop",
    "0..10",
    [TokenType.NUM, TokenType.DOTDOT, TokenType.NUM])


def test_lexer():
    """pytest entry point — runs all lexer test cases."""
    assert _passed == _total, f"Lexer tests: {_passed}/{_total} passed"


if __name__ == "__main__":
    print(f"\n{'='*40}")
    print(f"Result: {_passed}/{_total} passed")
