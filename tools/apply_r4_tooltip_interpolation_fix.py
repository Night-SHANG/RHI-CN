from pathlib import Path


path = Path("tools/transform.py")
text = path.read_text(encoding="utf-8")
old = '''        if expr.startswith('$"'):
            continue
'''
new = '''        if expr.startswith('$"') and expr.endswith('"'):
            fmt, args, has_english = _split_interpolated_body(expr[2:-1])
            if args and has_english:
                key = _cs_key(relpath, fmt, "ToolTipService.SetToolTip:interpolated")
                entries[key] = fmt
                fallback = _encode_csharp_string(fmt)
                rendered_args = ', '.join(f'$"{{{arg}}}"' for arg in args)
                localized = (
                    f'RenoDXCommander.Services.LocalizationService.Format("{key}", "{fallback}"'
                    + (f', {rendered_args}' if rendered_args else '') + ')'
                )
                replacements.append((start, end, f'ToolTipService.SetToolTip({target}, {localized})'))
            continue
'''
if old not in text:
    raise RuntimeError("interpolated tooltip anchor not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
