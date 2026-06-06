"""Parser and semantic checker smoke tests for assignment 1."""

import json

try:
    from lexer import Lexer
    from parser import Parser, format_ast_json, format_ast_tree
    from semantic import SemanticChecker
except ModuleNotFoundError:
    from lexer import Lexer
    from parser import Parser, format_ast_json, format_ast_tree
    from semantic import SemanticChecker


_passed = 0
_total = 0


def _parse_program(source):
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    program = parser.parse()
    return lexer, parser, program


def _run_parse_ok(name, source):
    global _passed, _total
    _total += 1
    lexer, parser, _ = _parse_program(source)
    ok = (len(lexer.errors) == 0) and (len(parser.errors) == 0)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        print("  lex errors:", lexer.errors)
        print("  parse errors:", parser.errors)
    if ok:
        _passed += 1


def _run_parse_error(name, source):
    """Expect at least one parse error."""
    global _passed, _total
    _total += 1
    lexer, parser, _ = _parse_program(source)
    ok = len(lexer.errors) == 0 and len(parser.errors) > 0
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        print("  lex errors:", lexer.errors)
        print("  parse errors:", parser.errors)
        print("  expected: at least 1 parse error")
    if ok:
        _passed += 1


def _run_parse_error_count(name, source, expected_count):
    """Expect an exact number of parse errors."""
    global _passed, _total
    _total += 1
    lexer, parser, _ = _parse_program(source)
    ok = len(lexer.errors) == 0 and len(parser.errors) == expected_count
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        print("  lex errors:", lexer.errors)
        print(f"  parse errors (expected {expected_count}, got {len(parser.errors)}):", parser.errors)
    if ok:
        _passed += 1


def _run_semantic(name, source, expect_error_substring=None):
    global _passed, _total
    _total += 1
    lexer, parser, program = _parse_program(source)

    ok = len(lexer.errors) == 0 and len(parser.errors) == 0
    sem_errors = []
    if ok:
        checker = SemanticChecker()
        sem_errors = checker.check(program)
        if expect_error_substring is None:
            ok = len(sem_errors) == 0
        else:
            ok = any(expect_error_substring in e for e in sem_errors)

    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        print("  lex errors:", lexer.errors)
        print("  parse errors:", parser.errors)
        print("  semantic errors:", sem_errors)

    if ok:
        _passed += 1


def _run_semantic_count(name, source, expected_error_count):
    """Expect a specific number of semantic errors."""
    global _passed, _total
    _total += 1
    lexer, parser, program = _parse_program(source)

    ok = len(lexer.errors) == 0 and len(parser.errors) == 0
    sem_errors = []
    if ok:
        checker = SemanticChecker()
        sem_errors = checker.check(program)
        ok = len(sem_errors) == expected_error_count

    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        print("  lex errors:", lexer.errors)
        print("  parse errors:", parser.errors)
        print(f"  semantic errors (expected {expected_error_count}, got {len(sem_errors)}):", sem_errors)

    if ok:
        _passed += 1


def _run_output_format(name, source):
    global _passed, _total
    _total += 1
    lexer, parser, program = _parse_program(source)
    ok = len(lexer.errors) == 0 and len(parser.errors) == 0
    detail = ""
    if ok:
        try:
            ast_json = format_ast_json(program)
            ast_tree = format_ast_tree(program)
            obj = json.loads(ast_json)
            ok = isinstance(obj, dict) and "functions" in obj and "AST Tree" in ast_tree
        except Exception as exc:  # pragma: no cover - defensive
            ok = False
            detail = str(exc)

    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        print("  lex errors:", lexer.errors)
        print("  parse errors:", parser.errors)
        print("  detail:", detail)

    if ok:
        _passed += 1


# ================================================================
# 1. 基本函数声明（规则 1.x）
# ================================================================

_run_parse_ok("1.1 basic function",
    "fn program_1_1() {}")

_run_parse_ok("1.2 empty statements",
    "fn program_1_2() { ;;;;;; }")

_run_parse_ok("1.3 return empty",
    "fn program_1_3() { return ; }")

_run_parse_ok("1.4 fn input",
    "fn program_1_4(mut a:i32) {}")

_run_parse_ok("1.5 fn output",
    "fn program_1_5() -> i32 { return 1; }")

_run_parse_ok("1.6 fn with multiple params",
    "fn add(mut a:i32, mut b:i32) -> i32 { a+b }")

_run_parse_ok("1.7 fn with immutable param",
    "fn foo(a:i32) { }")

_run_parse_ok("1.8 fn with ref param",
    "fn foo(a:&i32) { }")

_run_parse_ok("1.9 fn with mutable ref param",
    "fn foo(a:&mut i32) { }")

_run_parse_ok("1.10 fn with array param",
    "fn foo(a:[i32;3]) { }")

_run_parse_ok("1.11 fn with tuple param",
    "fn foo(a:(i32,i32)) { }")

_run_parse_ok("1.12 fn with array return",
    "fn foo() -> [i32;2] { [1,2] }")

_run_parse_ok("1.13 fn with tuple return",
    "fn foo() -> (i32,i32) { (1,2) }")

_run_parse_ok("1.14 multiple functions",
    """
fn a() {}
fn b() {}
fn c() {}
""".strip())


# ================================================================
# 2. 变量声明与赋值（规则 2.x）
# ================================================================

_run_parse_ok("2.1 var declarations",
    "fn f() { let mut a; let mut b:i32; }")

_run_parse_ok("2.2 assignment",
    "fn f(mut a:i32) { a=32; }")

_run_parse_ok("2.3 let + init",
    "fn f() { let mut a=1; let mut b:i32=1; }")

_run_parse_ok("2.4 let immutable with type",
    "fn f() { let x:i32; }")

_run_parse_ok("2.5 let immutable with init",
    "fn f() { let x:i32=42; }")

_run_parse_ok("2.6 let mutable without type or init",
    "fn f() { let mut x; }")

_run_parse_ok("2.7 let with complex init expr",
    "fn f() { let mut x=1+2*3; }")

_run_parse_ok("2.8 assignment to array index",
    "fn f(mut a:[i32;3]) { a[0]=1; }")

_run_parse_ok("2.9 assignment to tuple field",
    "fn f(mut a:(i32,i32)) { a.0=1; }")

_run_parse_ok("2.10 assignment to deref",
    "fn f(a:&mut i32) { *a=3; }")

_run_parse_ok("2.11 let with ref init",
    "fn f(a:i32) { let b:&i32=&a; }")

_run_parse_ok("2.12 let with mutable ref init",
    "fn f(mut a:i32) { let mut b:&mut i32=&mut a; }")


# ================================================================
# 3. 表达式（规则 3.x）
# ================================================================

_run_parse_ok("3.1 number expressions",
    "fn f() { 0; (1); ((2)); (((3))); }")

_run_parse_ok("3.1b variable expressions",
    "fn f(mut a:i32) { a; (a); ((a)); (((a))); }")

_run_parse_ok("3.2 comparison",
    "fn f() { 1<2; 3>4; 1<=2; 3>=4; 1==2; 1!=2; }")

_run_parse_ok("3.3 additive",
    "fn f() { 1+2; 3-4; }")

_run_parse_ok("3.4 multiplicative",
    "fn f() { 1*2; 3/4; }")

_run_parse_ok("3.5 function call",
    "fn a() {} fn b() { a(); }")

_run_parse_ok("3.5b function call with args",
    "fn a(x:i32,y:i32) {} fn b() { a(1,2); }")

_run_parse_ok("3.6 chained comparisons",
    "fn f() { 1<2; 2>1; 3>=3; 3<=3; 3==3; 3!=4; }")

_run_parse_ok("3.7 mixed precedence",
    "fn f() { 1+2*3; (1+2)*3; 1*2+3; }")

_run_parse_ok("3.8 nested arithmetic",
    "fn f() { (1+2)*(3-4)/(5+6); }")

_run_parse_ok("3.9 unary &",
    "fn f(a:i32) { &a; }")

_run_parse_ok("3.10 unary &mut",
    "fn f(mut a:i32) { &mut a; }")

_run_parse_ok("3.11 unary deref",
    "fn f(a:&i32) { *a; }")

_run_parse_ok("3.12 chained deref",
    "fn f(a:&&i32) { **a; }")

_run_parse_ok("3.13 index access",
    "fn f(a:[i32;3]) { a[0]; a[1+2]; }")

_run_parse_ok("3.14 tuple field access",
    "fn f(a:(i32,i32)) { a.0; a.1; }")

_run_parse_ok("3.15 chained call and index",
    """
fn get_arr() -> [i32;3] { [1,2,3] }
fn f() { get_arr()[0]; }
""".strip())


# ================================================================
# 4. if 语句（规则 4.x）
# ================================================================

_run_parse_ok("4.1 if only",
    "fn f(a:i32) -> i32 { if a>0 { return 1; } }")

_run_parse_ok("4.2 if else",
    "fn f(a:i32) -> i32 { if a>0 { return 1; } else { return 0; } }")

_run_parse_ok("4.3 if else-if else",
    "fn f(a:i32) -> i32 { if a>0 { return a+1; } else if a<0 { return a-1; } else { return 0; } }")

_run_parse_ok("4.4 nested if",
    "fn f(a:i32,b:i32) { if a>0 { if b>0 { } } }")

_run_parse_ok("4.5 nested if-else",
    "fn f(a:i32,b:i32) { if a>0 { if b>0 { } else { } } else { } }")

_run_parse_ok("4.6 three levels of else-if",
    "fn f(a:i32) { if a==1 { } else if a==2 { } else if a==3 { } else { } }")

_run_parse_ok("4.7 if with compound comparison",
    "fn f(a:i32,b:i32) { if a>0 { if b>0 { } } }")


# ================================================================
# 5. 循环语句（规则 5.x）
# ================================================================

_run_parse_ok("5.1 while",
    "fn f(mut n:i32) { while n>0 { n=n-1; } }")

_run_parse_ok("5.2 for range",
    "fn f(mut n:i32) { for mut i in 1..n+1 { n=n-1; } }")

_run_parse_ok("5.3 loop",
    "fn f() { loop { } }")

_run_parse_ok("5.4 break continue",
    "fn f() { while 1==0 { continue; } while 1==1 { break; } }")

_run_parse_ok("5.5 for with array",
    "fn f() { let mut a:[i32;3]=[1,2,3]; for mut i in a { } }")

_run_parse_ok("5.6 for with type annotation",
    "fn f() { let mut a:[i32;3]=[1,2,3]; for mut i:i32 in a { } }")

_run_parse_ok("5.7 nested loops",
    "fn f() { for mut i in 0..10 { for mut j in 0..10 { } } }")

_run_parse_ok("5.8 while with break",
    "fn f(mut n:i32) { while n>0 { if n==5 { break; } n=n-1; } }")

_run_parse_ok("5.9 loop with break value",
    "fn f() { let mut x=loop { break 42; }; }")

_run_parse_ok("5.10 for with range and complex body",
    "fn f(mut n:i32) { for mut i in 0..n { let mut x:i32=i*i; } }")

_run_parse_ok("5.11 break with expression",
    "fn f() { let mut x=loop { break 1+2; }; }")


# ================================================================
# 6. 引用与解引用（规则 6.x）
# ================================================================

_run_parse_ok("6.1 immutable attribute",
    "fn f() { let a:i32; let b; let c:i32=1; let d=2; }")

_run_parse_ok("6.2 immutable reference",
    "fn f(a:i32) { let b:&i32=&a; }")

_run_parse_ok("6.3 references",
    "fn f(mut a:i32) { let mut b:&mut i32=&mut a; }")

_run_parse_ok("6.4 borrow and deref",
    "fn f(a:&mut i32) { let b=*a; *a=3; }")

_run_parse_ok("6.5 deref in expression",
    "fn f(a:&mut i32) { let mut b:i32=*a+1; }")


# ================================================================
# 7. 表达式块（规则 7.x）
# ================================================================

_run_parse_ok("7.1 function expression block",
    "fn f(mut x:i32,mut y:i32) { let mut z={ let mut t=x*x+x; t=t+x*y; t }; }")

_run_parse_ok("7.2 function expr block as body",
    "fn f(mut x:i32,mut y:i32) -> i32 { let mut t=x*x+x; t=t+x*y; t }")

_run_parse_ok("7.3 if expression",
    "fn f(mut a:i32) { let mut b=if a>0 { 1 } else { 0 }; }")

_run_parse_ok("7.4 loop expression with break value",
    "fn f() { let mut a=loop { break 2; }; }")

_run_parse_ok("7.5 nested blocks",
    "fn f() { let mut x={ let mut a=1; { let mut b=2; a+b } }; }")

_run_parse_ok("7.6 block as expression in arithmetic",
    "fn f() { let mut x={ 1 }+{ 2 }; }")


# ================================================================
# 8. 数组（规则 8.x）
# ================================================================

_run_parse_ok("8.1 array type",
    "fn f() { let mut a:[i32;3]; }")

_run_parse_ok("8.2 array expression",
    "fn f(mut a:[i32;3]) { a=[1,2,3]; }")

_run_parse_ok("8.3 array index",
    "fn f(mut a:[i32;3]) { let mut b:i32=a[0]; a[0]=1; }")

_run_parse_ok("8.4 single element array",
    "fn f() { let mut a:[i32;1]=[42]; }")

_run_parse_ok("8.5 array with complex elements",
    "fn f() { let mut a:[i32;3]=[1+2,3*4,5-6]; }")

_run_parse_ok("8.6 nested array index",
    "fn f(mut a:[i32;3]) { let mut x:i32=a[1+1]; }")


# ================================================================
# 9. 元组（规则 9.x）
# ================================================================

_run_parse_ok("9.1 tuple type",
    "fn f() { let a:(i32,i32); }")

_run_parse_ok("9.2 tuple expression",
    "fn f(mut a:(i32,i32)) { a=(1,2); }")

_run_parse_ok("9.3 tuple field",
    "fn f(mut a:(i32,i32)) { let mut b:i32=a.0; a.0=1; }")

_run_parse_ok("9.4 triple tuple",
    "fn f() { let a:(i32,i32,i32)=(1,2,3); }")

_run_parse_ok("9.5 nested tuple",
    "fn f() { let a:((i32,i32),i32)=((1,2),3); }")

_run_parse_ok("9.6 tuple with array element",
    "fn f() { let a:([i32;2],i32)=([1,2],3); }")


# ================================================================
# 10. 语法错误检测
# ================================================================

_run_parse_error("err: missing semicolon after let",
    "fn f() { let x:i32=1 }")

_run_parse_error("err: trailing operator missing operand",
    "fn f() { 1+; }")

_run_parse_error("err: missing closing brace",
    "fn f() { let x:i32=1; ")

_run_parse_error("err: missing opening brace",
    "fn f() let x:i32=1; }")

_run_parse_error("err: missing closing paren",
    "fn f( { }")

_run_parse_error("err: missing fn keyword",
    "main() { }")

_run_parse_error("err: missing function name",
    "fn () { }")

_run_parse_error("err: missing colon in param",
    "fn f(a i32) { }")

_run_parse_error("err: missing type after colon in param",
    "fn f(a:) { }")

_run_parse_error("err: if without body",
    "fn f() { if 1>0 }")

_run_parse_error("err: while without body",
    "fn f() { while 1>0 }")

_run_parse_error("err: for without in",
    "fn f() { for mut i 0..10 { } }")

_run_parse_error("err: for without body",
    "fn f() { for mut i in 0..10 }")

_run_parse_error("err: return expression missing semicolon",
    "fn f() -> i32 { return 1 }")

_run_parse_error("err: break expression missing semicolon",
    "fn f() { loop { break 1 } }")

_run_parse_error("err: array type missing semicolon",
    "fn f() { let a:[i32 3]; }")

_run_parse_error("err: array type missing size",
    "fn f() { let a:[i32;]; }")

_run_parse_error("err: tuple field not a number",
    "fn f(a:(i32,i32)) { a.x; }")


# ================================================================
# 10b. 多错误恢复
# ================================================================

_run_parse_error_count("err-multi: two missing semicolons in one fn",
    "fn f() { let a:i32=1\n let b:i32=2\n }", 2)

_run_parse_error_count("err-multi: errors in different fns",
    "fn f() { let a:i32=1\n } fn g() { let b:i32=2\n }", 2)

_run_parse_error_count("err-multi: three errors in one fn",
    "fn f() { let a:i32=1\n let b:i32=2\n let c:i32=3\n }", 3)

_run_parse_error_count("err-multi: mixed error types",
    "fn f() { 1+\n let x:i32=1\n }", 2)

_run_parse_error_count("err-multi: error then valid stmt then error",
    "fn f() { let a:i32=1\n let b:i32=2; let c:i32=3\n }", 2)

_run_parse_error_count("err-multi: no errors still works",
    "fn f() { let a:i32=1; let b:i32=2; }", 0)


# ================================================================
# 11. 语义检查 — 不可变性约束（页面20）
# ================================================================

_run_semantic("sem: immutability assignment error",
    "fn f() { let a:i32=1; a=2; }",
    expect_error_substring="不可变左值")

_run_semantic("sem: immutable param assignment error",
    "fn f(a:i32) { a=2; }",
    expect_error_substring="不可变左值")

_run_semantic("sem: mutable variable ok",
    "fn f() { let mut a:i32=1; a=2; }")

_run_semantic("sem: mutable param ok",
    "fn f(mut a:i32) { a=2; }")


# ================================================================
# 12. 语义检查 — 类型匹配约束（页面20）
# ================================================================

_run_semantic("sem: type mismatch assignment error",
    "fn f() { let mut a:[i32;2]=[1,2]; a=1; }",
    expect_error_substring="类型不匹配")

_run_semantic("sem: let type mismatch",
    "fn f() { let a:i32=[1,2]; }",
    expect_error_substring="不匹配")

_run_semantic("sem: return type mismatch",
    "fn f() -> i32 { [1,2] }",
    expect_error_substring="不匹配")

_run_semantic("sem: let type ok",
    "fn f() { let a:i32=1; }")

_run_semantic("sem: return type ok",
    "fn f() -> i32 { 42 }")


# ================================================================
# 13. 语义检查 — for 循环可迭代约束（页面20）
# ================================================================

_run_semantic("sem: for non-iterable error",
    "fn f() { let mut x:i32=1; for mut i in x { x=x+1; } }",
    expect_error_substring="for 循环仅允许遍历区间表达式或数组表达式")

_run_semantic("sem: for array iterable ok",
    "fn f() { let mut a:[i32;3]=[1,2,3]; for mut i in a { let mut b:i32=i; } }")

_run_semantic("sem: for range iterable ok",
    "fn f(mut n:i32) { for mut i in 0..n { let mut x:i32=i; } }")


# ================================================================
# 14. 语义检查 — 未定义变量
# ================================================================

_run_semantic("sem: undefined variable in expr",
    "fn f() { x; }",
    expect_error_substring="未定义变量")

_run_semantic("sem: undefined variable in assignment",
    "fn f() { x=1; }",
    expect_error_substring="未定义变量")

_run_semantic("sem: variable from outer scope ok",
    "fn f() { let mut x:i32=1; { x=2; } }")


# ================================================================
# 15. 语义检查 — 重复定义
# ================================================================

_run_semantic("sem: duplicate variable declaration",
    "fn f() { let a:i32=1; let a:i32=2; }",
    expect_error_substring="重复定义")

_run_semantic("sem: shadow in inner scope ok",
    "fn f() { let a:i32=1; { let a:i32=2; } }")


# ================================================================
# 16. 语义检查 — break/continue 作用域
# ================================================================

_run_semantic("sem: break outside loop",
    "fn f() { break; }",
    expect_error_substring="break 只能出现在循环中")

_run_semantic("sem: continue outside loop",
    "fn f() { continue; }",
    expect_error_substring="continue 只能出现在循环中")

_run_semantic("sem: break inside loop ok",
    "fn f() { loop { break; } }")

_run_semantic("sem: continue inside while ok",
    "fn f() { while 1==1 { continue; } }")


# ================================================================
# 17. 语义检查 — 解引用
# ================================================================

_run_semantic("sem: deref non-reference error",
    "fn f() { let a:i32=1; let b=*a; }",
    expect_error_substring="解引用操作数不是引用")

_run_semantic("sem: deref reference ok",
    "fn f(a:&i32) { let b:i32=*a; }")

_run_semantic("sem: deref mutable reference ok",
    "fn f(a:&mut i32) { let b:i32=*a; }")


# ================================================================
# 18. 语义检查 — 数组操作
# ================================================================

_run_semantic("sem: index non-array error",
    "fn f() { let a:i32=1; let b=a[0]; }",
    expect_error_substring="仅数组支持下标访问")

_run_semantic("sem: array index ok",
    "fn f() { let a:[i32;3]=[1,2,3]; let b:i32=a[0]; }")

_run_semantic("sem: array element type mismatch",
    "fn f() { let a:[i32;2]=[1,[1,2]]; }",
    expect_error_substring="数组字面量元素类型不一致")

_run_semantic("sem: assign to immutable array element",
    "fn f() { let a:[i32;3]=[1,2,3]; a[0]=42; }",
    expect_error_substring="不可变左值")


# ================================================================
# 19. 语义检查 — 元组操作
# ================================================================

_run_semantic("sem: tuple field out of bounds",
    "fn f() { let a:(i32,i32)=(1,2); let b=a.2; }",
    expect_error_substring="元组索引越界")

_run_semantic("sem: tuple field ok",
    "fn f() { let a:(i32,i32)=(1,2); let b:i32=a.0; }")

_run_semantic("sem: field access on non-tuple",
    "fn f() { let a:i32=1; let b=a.0; }",
    expect_error_substring="仅元组支持")


# ================================================================
# 20. 语义检查 — 算术运算
# ================================================================

_run_semantic("sem: arithmetic on non-i32 error",
    "fn f() { let a:[i32;2]=[1,2]; let b:i32=a+1; }",
    expect_error_substring="算术运算要求两侧为 i32")


# ================================================================
# 21. 语义检查 — if 表达式分支类型
# ================================================================

_run_semantic("sem: if expr branch type mismatch",
    "fn f() { let mut x=if 1>0 { 1 } else { [1,2] }; }",
    expect_error_substring="if 表达式两个分支类型不一致")


# ================================================================
# 22. AST 输出格式
# ================================================================

_run_output_format("ast output: json and tree",
    "fn out_demo(mut a:i32) -> i32 { if a>0 { return a; } a }")

_run_output_format("ast: multiple functions",
    "fn a() {} fn b(x:i32) -> i32 { x }")

_run_output_format("ast: complex program",
    """
fn fib(mut n:i32) -> i32 {
    if n<=1 {
        return n;
    }
    let mut a:i32=0;
    let mut b:i32=1;
    for mut i in 2..n+1 {
        let mut t:i32=a+b;
        a=b;
        b=t;
    }
    b
}
""".strip())


def test_parser():
    """pytest entry point — runs all parser/semantic test cases."""
    assert _passed == _total, f"Parser tests: {_passed}/{_total} passed"


if __name__ == "__main__":
    print(f"\n{'='*40}")
    print(f"Result: {_passed}/{_total} passed")
