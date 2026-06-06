"""JSON bridge for lexer/parser frontend integration.

Reads source code from stdin and prints a JSON payload with lexical,
syntactic, and semantic analysis results.
"""

from __future__ import annotations

import json
import re
import sys

from lexer import Lexer, TokenType
from parser import Parser, SemanticChecker, format_ast_summary, format_ast_tree, program_to_dict
from diagnostics import Diagnostic


def _configure_utf8_stdio() -> None:
    """Ensure stable UTF-8 output for frontend bridge on Windows."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


_DIAGNOSTIC_LINE_RE = re.compile(r"^Ln\s+(\d+):(\d+)\s+[^:：]*[:：]\s*(.*)$")


def _diagnostics_from_strings(phase: str, errors: list[str]) -> list[dict]:
    diagnostics = []
    for err in errors:
        match = _DIAGNOSTIC_LINE_RE.match(err)
        if match:
            line = int(match.group(1))
            column = int(match.group(2))
            message = match.group(3)
        else:
            line = 0
            column = 0
            message = err
        diagnostics.append(Diagnostic(phase=phase, message=message, line=line, column=column).to_dict())
    return diagnostics


def analyze_source(source: str) -> dict:
    lexer = Lexer(source)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    program = parser.parse()

    checker = SemanticChecker()
    semantic_errors = checker.check(program) if not parser.errors else []
    semantic_diagnostics = [d.to_dict() for d in checker.diagnostics] if not parser.errors else []

    token_rows = []
    for tok in tokens:
        if tok.token_type == TokenType.EOF:
            continue
        token_rows.append(
            {
                "type": tok.token_type.name,
                "value": tok.value,
                "line": tok.line,
                "column": tok.column,
            }
        )

    return {
        "ok": len(lexer.errors) == 0 and len(parser.errors) == 0 and len(semantic_errors) == 0,
        "tokens": token_rows,
        "lexErrors": lexer.errors,
        "parseErrors": parser.errors,
        "semanticErrors": semantic_errors,
        "lexDiagnostics": _diagnostics_from_strings("lexical", lexer.errors),
        "parseDiagnostics": [d.to_dict() for d in parser.diagnostics],
        "semanticDiagnostics": semantic_diagnostics,
        "astSummary": format_ast_summary(program),
        "astTree": format_ast_tree(program),
        "ast": program_to_dict(program),
    }


def main() -> None:
    _configure_utf8_stdio()
    source = sys.stdin.read()
    result = analyze_source(source)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
