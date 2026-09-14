from pathlib import Path


path = Path("tools/transform.py")
text = path.read_text(encoding="utf-8")

helper_anchor = "\ndef _transform_tooltips(text: str, relpath: str) -> tuple[str, dict[str, str]]:\n"
helper = r'''
def _split_top_level_ternary(expr: str) -> tuple[str, str, str] | None:
    """Split a simple C# ternary while ignoring strings and nested delimiters."""
    question = -1
    nested_ternaries = 0
    stack: list[str] = []
    quote: str | None = None
    i = 0
    pairs = {')': '(', ']': '[', '}': '{'}
    while i < len(expr):
        ch = expr[i]
        if quote is not None:
            if ch == '\\':
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in {'"', "'"}:
            quote = ch
            i += 1
            continue
        if ch in '([{':
            stack.append(ch)
            i += 1
            continue
        if ch in ')]}':
            if stack and stack[-1] == pairs[ch]:
                stack.pop()
            i += 1
            continue
        if stack:
            i += 1
            continue
        if ch == '?' and i + 1 < len(expr) and expr[i + 1] in {'?', '.'}:
            i += 2
            continue
        if ch == '?':
            if question < 0:
                question = i
            else:
                nested_ternaries += 1
            i += 1
            continue
        if ch == ':' and question >= 0:
            if nested_ternaries:
                nested_ternaries -= 1
            else:
                return expr[:question], expr[question + 1:i], expr[i + 1:]
        i += 1
    return None
'''

if "def _split_top_level_ternary(" not in text:
    if helper_anchor not in text:
        raise RuntimeError("tooltip helper insertion anchor not found")
    text = text.replace(helper_anchor, helper + helper_anchor, 1)

old = r'''        if '?' in expr and literal_any.search(expr):
            def repl_literal(m: re.Match) -> str:
                value = _decode_csharp_string(m.group(1))
                if not value.strip() or not any(ch.isalpha() for ch in value):
                    return m.group(0)
                key = _cs_key(relpath, value, "ToolTipService.SetToolTip:branch")
                entries[key] = value
                fallback = _encode_csharp_string(value)
                return f'RenoDXCommander.Services.LocalizationService.GetString("{key}", "{fallback}")'
            localized_expr = literal_any.sub(repl_literal, expr)
            replacements.append((start, end, f'ToolTipService.SetToolTip({target}, {localized_expr})'))
            continue
'''

new = r'''        if '?' in expr:
            ternary = _split_top_level_ternary(expr)
            if ternary:
                condition, yes_branch, no_branch = ternary

                def localize_branch(branch: str) -> tuple[str, bool]:
                    branch = branch.strip()
                    if branch.startswith('$"') and branch.endswith('"'):
                        fmt, args, has_english = _split_interpolated_body(branch[2:-1])
                        if args and has_english:
                            key = _cs_key(relpath, fmt, "ToolTipService.SetToolTip:interpolated")
                            entries[key] = fmt
                            fallback = _encode_csharp_string(fmt)
                            rendered_args = ', '.join(f'$"{{{arg}}}"' for arg in args)
                            localized = (
                                f'RenoDXCommander.Services.LocalizationService.Format("{key}", "{fallback}"'
                                + (f', {rendered_args}' if rendered_args else '') + ')'
                            )
                            return localized, True
                        return branch, False

                    plain_branch = literal_full.fullmatch(branch)
                    if plain_branch:
                        value = _decode_csharp_string(plain_branch.group(1))
                        if value.strip() and any(ch.isalpha() for ch in value):
                            key = _cs_key(relpath, value, "ToolTipService.SetToolTip:branch")
                            entries[key] = value
                            fallback = _encode_csharp_string(value)
                            localized = (
                                f'RenoDXCommander.Services.LocalizationService.GetString('
                                f'"{key}", "{fallback}")'
                            )
                            return localized, True
                    return branch, False

                localized_yes, yes_changed = localize_branch(yes_branch)
                localized_no, no_changed = localize_branch(no_branch)
                if yes_changed or no_changed:
                    localized_expr = (
                        f'{condition.strip()} ? {localized_yes} : {localized_no}'
                    )
                    replacements.append(
                        (start, end, f'ToolTipService.SetToolTip({target}, {localized_expr})')
                    )
                    continue
'''

if old not in text:
    if "localized_yes, yes_changed = localize_branch(yes_branch)" not in text:
        raise RuntimeError("ternary tooltip anchor not found")
else:
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
