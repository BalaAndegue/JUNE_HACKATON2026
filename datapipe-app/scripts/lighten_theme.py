"""
One-shot theme converter: flips the hardcoded dark palette to a clean,
professional LIGHT theme across all components, while preserving the
semantic accent colors (orange/green/blue/amber/red node & status colors).

Deterministic ordered string replacements. Run from datapipe-app/:
    python scripts/lighten_theme.py
"""
import pathlib

SRC = pathlib.Path('src')

# Ordered (longer/specific first). Accent colors are intentionally NOT mapped.
REPLACEMENTS = [
    # ── deep app backgrounds -> light app bg ──
    ('#0a0a0b', '#f4f6f9'), ('#0a0a0a', '#f4f6f9'), ('#08080c', '#f4f6f9'),
    ('#050505', '#f4f6f9'), ('#0d0d0d', '#f4f6f9'), ('#0f0f13', '#eceff3'),
    ('#0f0f0f', '#f4f6f9'),
    # ── elevated surfaces / cards -> white ──
    ('#111116', '#ffffff'), ('#111111', '#ffffff'), ('#141414', '#ffffff'),
    ('#151515', '#ffffff'), ('#121212', '#ffffff'), ('#161616', '#ffffff'),
    ('#181818', '#f1f3f6'), ('#1a1a1a', '#f1f3f6'), ('#1c1c1c', '#f1f3f6'),
    # ── borders ──
    ('#1e1e1e', '#e6e8ec'), ('#222222', '#e6e8ec'), ('#232323', '#e6e8ec'),
    ('#2a2a2a', '#d7dbe2'), ('#333333', '#cfd4dc'), ('#3a3a3a', '#c3c9d2'),
    # ── default foreground (light text -> dark text) ──
    ('#e5e5e5', '#1c2230'), ('#e5e7eb', '#1c2230'), ('#f0f0f0', '#1c2230'),
    ('#d4d4d4', '#3a4252'),
    # ── inline rgba white overlays -> subtle dark overlays ──
    ('rgba(255,255,255,0.1)', 'rgba(15,23,42,0.10)'),
    ('rgba(255,255,255,0.08)', 'rgba(15,23,42,0.08)'),
    ('rgba(255,255,255,0.07)', 'rgba(15,23,42,0.07)'),
    ('rgba(255,255,255,0.06)', 'rgba(15,23,42,0.07)'),
    ('rgba(255,255,255,0.05)', 'rgba(15,23,42,0.06)'),
    ('rgba(255,255,255,0.04)', 'rgba(15,23,42,0.05)'),
    ('rgba(255,255,255,0.03)', 'rgba(15,23,42,0.04)'),
    ('rgba(255, 255, 255, 0.1)', 'rgba(15,23,42,0.10)'),
    ('rgba(255, 255, 255, 0.06)', 'rgba(15,23,42,0.07)'),
    # ── tailwind white-overlay utilities -> dark overlays (slash form only) ──
    ('white/50', 'slate-900/40'), ('white/20', 'slate-900/15'),
    ('white/15', 'slate-900/10'), ('white/12', 'slate-900/10'),
    ('white/10', 'slate-900/10'), ('white/8', 'slate-900/[0.06]'),
    ('white/5', 'slate-900/5'), ('white/4', 'slate-900/[0.04]'),
    # ── light gray text -> readable dark on white ──
    ('text-gray-100', 'text-slate-900'), ('text-gray-200', 'text-slate-800'),
    ('text-gray-300', 'text-slate-700'), ('text-gray-400', 'text-slate-600'),
    ('text-gray-500', 'text-slate-500'), ('text-gray-600', 'text-slate-500'),
    ('text-white', 'text-slate-900'),
    # ── dark gray surfaces via tailwind ──
    ('bg-gray-900', 'bg-white'), ('bg-gray-800', 'bg-slate-100'),
    ('border-gray-800', 'border-slate-200'), ('border-gray-700', 'border-slate-200'),
    ('hover:bg-gray-800', 'hover:bg-slate-100'),
]


def main():
    changed = 0
    for path in list(SRC.rglob('*.tsx')) + list(SRC.rglob('*.ts')):
        text = path.read_text(encoding='utf-8')
        original = text
        for a, b in REPLACEMENTS:
            text = text.replace(a, b)
        if text != original:
            path.write_text(text, encoding='utf-8')
            changed += 1
            print(f"  light  {path}")
    print(f"\n{changed} fichiers rethémés.")


if __name__ == '__main__':
    main()
