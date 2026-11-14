"""Language-agnostic symbol extraction for design/code consistency (L3 v0.10).

Regex + per-language rule tables: enough for symbol-existence checks, no extra
dependencies. Filters language keywords and header-guard macros so design docs
mentioning `enum` or `GEMM_H` don't produce phantom inconsistencies.
"""

from __future__ import annotations

import re
from pathlib import Path

# Extensions scanned when manifest does not specify `code_extensions`
DEFAULT_CODE_EXTENSIONS: list[str] = [
    ".py", ".c", ".h", ".cc", ".cpp", ".hpp", ".rs", ".go", ".java", ".ts", ".tsx", ".js"
]

# Language keywords that must never be reported as missing symbols
KEYWORDS: set[str] = {
    # C / C++
    "auto", "bool", "break", "case", "catch", "char", "class", "const", "constexpr",
    "continue", "default", "delete", "do", "double", "else", "enum", "explicit",
    "extern", "false", "float", "for", "friend", "goto", "if", "inline", "int",
    "long", "mutable", "namespace", "new", "noexcept", "nullptr", "operator",
    "private", "protected", "public", "register", "return", "short", "signed",
    "sizeof", "static", "static_cast", "struct", "switch", "template", "this",
    "throw", "true", "try", "typedef", "typename", "union", "unsigned", "using",
    "virtual", "void", "volatile", "while",
    # Python
    "and", "as", "assert", "async", "await", "def", "del", "elif", "except",
    "finally", "from", "global", "import", "in", "is", "lambda", "nonlocal",
    "not", "or", "pass", "raise", "with", "yield", "False", "None", "True",
    # Rust
    "fn", "impl", "let", "match", "mod", "mut", "pub", "ref", "self", "trait",
    "where", "unsafe", "crate", "dyn",
    # Go
    "func", "go", "chan", "defer", "fallthrough", "interface", "map", "package",
    "range", "select", "type", "var",
    # Java / TS
    "abstract", "extends", "final", "implements", "instanceof", "native",
    "synchronized", "throws", "transient", "function", "export", "declare",
    # preprocessor / directive words
    "defined", "include", "ifdef", "ifndef", "endif", "else", "elif", "pragma",
    "undef", "error", "warning", "line",
}

# Symbols provided by toolchains/stdlib/build tools: they never need to be
# "implemented" in the project, so they must not be reported as missing.
EXTERNAL_SYMBOLS: set[str] = {
    # C/C++ stdlib & libc
    "printf", "fprintf", "snprintf", "sprintf", "puts", "malloc", "calloc",
    "realloc", "free", "memcpy", "memset", "memmove", "strlen", "strcmp",
    "strcpy", "rand", "srand", "clock_gettime", "clock", "getenv", "setenv",
    "atoi", "atof", "strtol", "sysconf", "pthread_create", "pthread_join",
    "sqrtf", "sqrt", "fabsf", "fabs", "fmax", "fmaxf", "fmin", "fminf",
    "expf", "logf", "powf", "floorf", "ceilf", "max", "min", "abs", "int",
    "double", "float", "char", "long", "short",
    # BLAS / Accelerate
    "cblas_sgemm", "cblas_dgemm",
    # build / shell commands commonly mentioned in docs
    "make", "cd", "ls", "cat", "ar", "cc", "clang", "gcc", "cmake", "git",
    "python", "pip", "npm", "pnpm",
    # python builtins & modules that appear in doc examples
    "sorted", "reversed", "enumerate", "zip", "len", "range", "open", "print",
    "dict", "list", "tuple", "str", "bytes", "isinstance", "getattr", "setattr",
    "json", "os", "re", "sys", "hashlib", "sha256", "uuid", "datetime",
    "items", "keys", "values", "append", "format", "join", "split", "strip",
    "lower", "upper", "replace", "startswith", "endswith", "read_text",
    "write_text", "exists", "mkdir", "glob", "rglob", "iterdir", "resolve",
    "expanduser", "parent", "stat", "now", "isoformat", "fromisoformat",
    "loads", "dumps", "MCP", "FILE", "README",
    # module / SQL object names mentioned in docs
    "vinw", "registry", "project_events", "projects", "consistency_reports",
}

# Header-guard style macros: FOO_H, VINW_GEMM_H, FOO_HPP, _FOO_H_
_GUARD_MACRO = re.compile(
    r"^_?[A-Z][A-Z0-9_]*(?:_H|_HPP|_HH|_INCLUDED|_INCLUDED_)_?$"
)

# Per-extension extraction rules (function/class/macro definitions)
LANGUAGE_RULES: dict[str, list[re.Pattern[str]]] = {
    ".py": [
        re.compile(r"^\s*(?:async\s+)?def\s+(\w+)", re.M),
        re.compile(r"^\s*class\s+(\w+)", re.M),
    ],
    ".c": [
        re.compile(r"^#\s*define\s+(\w+)", re.M),
        # definition only: name(...) {   (prototypes belong to headers)
        re.compile(r"\b([A-Za-z_]\w*)\s*\([^;{}\n]*\)\s*\{", re.M),
        re.compile(r"\b(?:struct|union|enum)\s+(\w+)\s*\{", re.M),
        re.compile(r"\btypedef\b[^;]*?\b(\w+)\s*;", re.M),
    ],
    ".h": [
        re.compile(r"^#\s*define\s+(\w+)", re.M),
        # declaration: name(...);  (headers usually only declare)
        re.compile(r"\b([A-Za-z_]\w*)\s*\([^;{}\n]*\)\s*;", re.M),
        re.compile(r"\b(?:struct|union|enum)\s+(\w+)\s*\{", re.M),
        re.compile(r"\btypedef\b[^;]*?\b(\w+)\s*;", re.M),
    ],
    ".rs": [
        re.compile(r"\bfn\s+(\w+)", re.M),
        re.compile(r"\b(?:struct|enum|trait|union)\s+(\w+)", re.M),
        re.compile(r"\bmacro_rules!\s*(\w+)", re.M),
    ],
    ".go": [
        re.compile(r"\bfunc\s+(?:\([^)]*\)\s*)?(\w+)", re.M),
        re.compile(r"^type\s+(\w+)", re.M),
    ],
    ".java": [
        re.compile(r"\b(?:class|interface|enum)\s+(\w+)", re.M),
        re.compile(r"\b[A-Za-z_][\w<>\[\],\s]*\s+(\w+)\s*\([^;{}\n]*\)\s*\{", re.M),
    ],
    ".ts": [
        re.compile(r"\bfunction\s+(\w+)", re.M),
        re.compile(r"\b(?:class|interface|enum|type)\s+(\w+)", re.M),
        re.compile(r"\bexport\s+const\s+(\w+)", re.M),
    ],
}
# Aliases reuse another language's rules
LANGUAGE_RULES[".cc"] = LANGUAGE_RULES[".c"]
LANGUAGE_RULES[".cpp"] = LANGUAGE_RULES[".c"]
LANGUAGE_RULES[".hpp"] = LANGUAGE_RULES[".h"]
LANGUAGE_RULES[".hh"] = LANGUAGE_RULES[".h"]
LANGUAGE_RULES[".tsx"] = LANGUAGE_RULES[".ts"]
LANGUAGE_RULES[".js"] = LANGUAGE_RULES[".ts"]


def is_code_file(path: Path, extensions: list[str] | None = None) -> bool:
    exts = [e.lower() for e in (extensions or DEFAULT_CODE_EXTENSIONS)]
    return path.suffix.lower() in exts


def filter_symbols(names) -> set[str]:
    """Drop language keywords and header-guard macros."""
    result: set[str] = set()
    for name in names:
        if not name or len(name) < 2:
            continue
        if name in KEYWORDS or name in EXTERNAL_SYMBOLS:
            continue
        # version-like tokens (v0, v001) are doc artifacts, not symbols
        if re.fullmatch(r"v\d+", name):
            continue
        if _GUARD_MACRO.match(name):
            continue
        # Reserved identifiers: _OPENMP, __GNUC__ ... provided by toolchains
        if re.fullmatch(r"_+[A-Z][A-Z0-9_]*", name):
            continue
        result.add(name)
    return result


def extract_code_symbols_with_lines(
    path: Path, extensions: list[str] | None = None
) -> dict[str, int]:
    """Symbol -> first 1-based line number where it is defined/declared."""
    suffix = path.suffix.lower()
    rules = LANGUAGE_RULES.get(suffix)
    if rules is None:
        rules = LANGUAGE_RULES[".py"]

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}

    found: dict[str, int] = {}

    def line_of(offset: int) -> int:
        return text.count("\n", 0, offset) + 1

    for pattern in rules:
        for m in pattern.finditer(text):
            name = m.group(1)
            if name not in found:
                found[name] = line_of(m.start())
    for m in _MACRO_REF.finditer(text):
        name = m.group(1) or m.group(2)
        if name and name not in found:
            found[name] = line_of(m.start())

    allowed = filter_symbols(found.keys())
    return {name: line for name, line in found.items() if name in allowed}


def extract_code_symbols(path: Path, extensions: list[str] | None = None) -> set[str]:
    """Definitions declared/defined in a code file, per-language."""
    suffix = path.suffix.lower()
    rules = LANGUAGE_RULES.get(suffix)
    if rules is None:
        # Unknown language: fall back to identifier-ish declarations
        rules = LANGUAGE_RULES[".py"]

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return set()

    return set(extract_code_symbols_with_lines(path, extensions))


# Candidate identifiers in design docs: backticked names, table code spans,
# and bare identifiers that look like API names.
# Build-flag macros referenced (not defined) still count as "present in code"
_MACRO_REF = re.compile(r"#\s*(?:ifdef|ifndef)\s+([A-Za-z_]\w*)|defined\s*\(?\s*([A-Za-z_]\w*)")

_BACKTICK = re.compile(r"`([A-Za-z_]\w*)`")
_IDENT = re.compile(r"[A-Za-z_]\w*")
_CODE_SPAN_CALL = re.compile(r"\b([A-Za-z_]\w*)\s*\(")


# Table headers that mark a table as an API surface listing
API_HEADER_KEYWORDS = (
    "接口", "工具", "函数", "命令", "方法", "api", "tool", "function", "command",
    "endpoint", "signature",
)


def _table_is_api(header: list[str]) -> bool:
    joined = " ".join(header).lower()
    if any(k in joined for k in API_HEADER_KEYWORDS):
        return True
    # a single-column table of identifiers is an API list by nature
    return len([h for h in header if h.strip()]) == 1


_FENCE_SIGNATURE = re.compile(r"^\s*(?:def|class|fn|func|interface|struct)\s+(\w+)|^\s*(\w+)\s*\(")
_SQL_JSON_HINT = re.compile(r"^\s*[{}\[\]]|\b(?:SELECT|CREATE|INSERT|UPDATE|PRAGMA)\b")


def _strip_code(text: str) -> tuple[str, set[str]]:
    """Split fenced blocks out, keeping only function-signature-like names.

    SQL/JSON examples must not count as required symbols, but a design doc that
    shows `def gemm_f32(...)` is declaring an API and must be enforced.
    """
    outside: list[str] = []
    declared: set[str] = set()
    fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if not fence:
            outside.append(line)
            continue
        if _SQL_JSON_HINT.search(line):
            continue
        m = _FENCE_SIGNATURE.match(line)
        if m:
            declared.add(m.group(1) or m.group(2))
    return "\n".join(outside), filter_symbols(declared)


def split_design_symbols(content: str) -> tuple[set[str], set[str]]:
    """Split design mentions into (required, advisory).

    required: identifiers listed in API tables or used in call form — the code
              must define these.
    advisory: other backticked mentions (config keys, enum values, prose) —
              reported for information, never blocking.
    """
    plain, fenced_decls = _strip_code(content)
    required: set[str] = set()
    advisory: set[str] = set()

    header: list[str] | None = None
    for line in plain.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            is_separator = all(set(c) <= set("-: ") for c in cells if c)
            if header is None:
                header = cells
                continue
            if is_separator:
                continue
            first = cells[0] if cells else ""
            idents = _IDENT.findall(first)
            if _table_is_api(header):
                # only the leading identifier is the API name, not its params
                if idents:
                    required |= filter_symbols(idents[:1])
            else:
                advisory |= filter_symbols(idents)
            continue
        header = None  # table ended

    required |= filter_symbols(
        name for name in _CODE_SPAN_CALL.findall(plain) if "_" in name
    )
    required |= fenced_decls
    advisory |= filter_symbols(_BACKTICK.findall(plain))
    return required, advisory - required


def extract_design_identifiers(content: str) -> set[str]:
    """Backwards-compatible union of required and advisory identifiers."""
    required, advisory = split_design_symbols(content)
    return required | advisory
