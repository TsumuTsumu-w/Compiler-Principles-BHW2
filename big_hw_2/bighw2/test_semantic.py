"""Semantic analyzer and quadruple generation tests."""

from __future__ import annotations

try:
    from lexer import Lexer
    from parser import Parser
    from semantic import SemanticAnalyzer
except ModuleNotFoundError:
    from bighw2.lexer import Lexer
    from bighw2.parser import Parser
    from bighw2.semantic import SemanticAnalyzer


_passed = 0
_total = 0


def _analyze(source: str):
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    program = parser.parse()
    result = None
    if not lexer.errors and not parser.errors:
        result = SemanticAnalyzer().analyze(program)
    return lexer, parser, result


def _pass(name: str, ok: bool, detail: str = "") -> None:
    global _passed, _total
    _total += 1
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok and detail:
        print(detail)
    if ok:
        _passed += 1


def _run_ok(name: str, source: str) -> None:
    lexer, parser, result = _analyze(source)
    ok = (
        len(lexer.errors) == 0
        and len(parser.errors) == 0
        and result is not None
        and len(result.errors) == 0
    )
    _pass(
        name,
        ok,
        f"  lex errors: {lexer.errors}\n  parse errors: {parser.errors}\n"
        f"  semantic errors: {result.errors if result else []}",
    )


def _run_error(name: str, source: str, expected_substrings: list[str], expected_count: int | None = None) -> None:
    lexer, parser, result = _analyze(source)
    errors = result.errors if result is not None else []
    ok = len(lexer.errors) == 0 and len(parser.errors) == 0 and result is not None
    if expected_count is not None:
        ok = ok and len(errors) == expected_count
    ok = ok and all(any(part in err for err in errors) for part in expected_substrings)
    _pass(
        name,
        ok,
        f"  lex errors: {lexer.errors}\n  parse errors: {parser.errors}\n"
        f"  semantic errors: {errors}\n  expected substrings: {expected_substrings}",
    )


def _run_diagnostic_location(name: str, source: str, line: int, column: int) -> None:
    lexer, parser, result = _analyze(source)
    diagnostics = result.diagnostics if result is not None else []
    ok = (
        len(lexer.errors) == 0
        and len(parser.errors) == 0
        and any(d.line == line and d.column == column for d in diagnostics)
    )
    _pass(
        name,
        ok,
        f"  diagnostics: {[d.to_dict() for d in diagnostics]}\n  expected: Ln {line}:{column}",
    )


def _run_signature_table(name: str, source: str, expected_names: list[str]) -> None:
    lexer, parser, result = _analyze(source)
    names = [row["name"] for row in result.function_signatures] if result is not None else []
    ok = len(lexer.errors) == 0 and len(parser.errors) == 0 and names == expected_names
    _pass(name, ok, f"  signatures: {names}\n  expected: {expected_names}")


def _run_ir_ops(name: str, source: str, expected_ops: list[str]) -> None:
    lexer, parser, result = _analyze(source)
    ops = [quad.op for quad in result.quads] if result is not None else []
    ok = (
        len(lexer.errors) == 0
        and len(parser.errors) == 0
        and result is not None
        and len(result.errors) == 0
        and all(op in ops for op in expected_ops)
    )
    _pass(
        name,
        ok,
        f"  semantic errors: {result.errors if result else []}\n  ops: {ops}\n  expected ops: {expected_ops}",
    )


# ---------- valid semantic programs ----------

_run_ok(
    "ok: variables, assignment, return",
    "fn f(mut a:i32) -> i32 { let mut b:i32=a+1; b=b*2; b }",
)

_run_ok(
    "ok: arrays and tuples",
    "fn f() { let a:[i32;3]=[1,2,3]; let t:(i32,i32)=(a[0],2); let x:i32=t.0; }",
)

_run_ok(
    "ok: references and dereference",
    "fn f(a:&mut i32) { let b:i32=*a; *a=b+1; }",
)

_run_ok(
    "ok: function call return type",
    "fn id(x:i32) -> i32 { x } fn f() { let y:i32=id(1); }",
)


# ---------- semantic diagnostics ----------

_run_error(
    "error: duplicate function",
    "fn dup() {} fn dup() {}",
    ["dup"],
)

_run_error(
    "error: duplicate variable",
    "fn f() { let a:i32=1; let a:i32=2; }",
    ["a"],
)

_run_error(
    "error: undefined variable",
    "fn f() { x; }",
    ["x"],
)

_run_error(
    "error: immutable assignment",
    "fn f() { let a:i32=1; a=2; }",
    ["Ln 1:23"],
)

_run_error(
    "error: assignment type mismatch",
    "fn f() { let mut a:[i32;2]=[1,2]; a=1; }",
    ["["],
)

_run_error(
    "error: return type mismatch",
    "fn f() -> i32 { [1,2] }",
    ["i32"],
)

_run_error(
    "error: undefined function",
    "fn f() { missing_fn(1); }",
    ["missing_fn"],
)

_run_error(
    "error: function arg count",
    "fn add(a:i32,b:i32) -> i32 { a+b } fn f() { let x:i32=add(1); }",
    ["add", "1"],
)

_run_error(
    "error: function arg type",
    "fn take_i32(x:i32) {} fn f() { let a:[i32;1]=[1]; take_i32(a); }",
    ["take_i32", "i32"],
)

_run_error(
    "error: break outside loop",
    "fn f() { break; }",
    ["break"],
)

_run_error(
    "error: continue outside loop",
    "fn f() { continue; }",
    ["continue"],
)

_run_error(
    "error: array element mismatch",
    "fn f() { let a:[i32;2]=[1,[1,2]]; }",
    ["Ln"],
)

_run_error(
    "error: tuple field out of bounds",
    "fn f() { let a:(i32,i32)=(1,2); let b=a.2; }",
    ["Ln"],
)

_run_error(
    "error: if expression branch type mismatch",
    "fn f() { let x=if 1>0 { 1 } else { [1,2] }; }",
    ["if"],
)

_run_diagnostic_location(
    "diagnostic location: immutable assignment",
    "fn f() {\n    let a:i32=1;\n    a=2;\n}",
    3,
    5,
)


# ---------- function signatures ----------

_run_signature_table(
    "signatures: collection order",
    "fn add(a:i32,b:i32) -> i32 { a+b } fn main() { add(1,2); }",
    ["add", "main"],
)


# ---------- quadruples ----------

_run_ir_ops(
    "ir: arithmetic assignment return",
    "fn f(mut a:i32) -> i32 { let mut b:i32=a+1; b=b*2; b }",
    ["func", "param", "+", "=", "*", "return", "endfunc"],
)

_run_ir_ops(
    "ir: function call",
    "fn inc(x:i32) -> i32 { x+1 } fn f() { let y:i32=inc(1); }",
    ["arg", "call", "="],
)

_run_ir_ops(
    "ir: while and if",
    "fn f(mut n:i32) { while n>0 { if n==1 { n=n-1; } } }",
    ["label", ">", "jz", "==", "-", "jmp"],
)

_run_ir_ops(
    "ir: for range",
    "fn f(mut n:i32) { for mut i in 0..n { n=n+i; } }",
    ["label", "<", "jz", "+", "jmp"],
)

_run_ir_ops(
    "ir: array tuple access",
    "fn f() { let a:[i32;2]=[1,2]; let t:(i32,i32)=(a[0],2); let x=t.0; }",
    ["array", "array_set", "[]", "tuple", "tuple_set", "."],
)


print(f"\n{'=' * 40}")
print(f"Semantic result: {_passed}/{_total} passed")


def test_semantic():
    """pytest entry point for semantic analyzer tests."""
    assert _passed == _total, f"Semantic tests: {_passed}/{_total} passed"


if __name__ == "__main__":
    raise SystemExit(0 if _passed == _total else 1)
