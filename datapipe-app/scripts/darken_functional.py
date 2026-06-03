"""Re-darken ONLY the color tokens in the kept functional files (logic untouched),
to restore Jeff's original dark colorimetry. Inverse of lighten_theme.py."""
import re, pathlib

FILES = [
    'src/components/editor/AIChatPanel.tsx',
    'src/components/editor/EditorTopBar.tsx',
    'src/components/editor/CanvasControls.tsx',
    'src/components/editor/RunConsole.tsx',
    'src/components/editor/EditorCanvas.tsx',
    'src/app/demo/page.tsx',
    'src/app/(dashboard)/dashboard/pipelines/page.tsx',
]

# Ordered. Accent colors (#ff6d35, emerald/amber/red/purple/sky text, bg-slate-900 code) kept.
REPL = [
    (r'\bbg-white\b', 'bg-[#141414]'),          # bare bg-white surfaces -> dark card
    ('text-slate-900', 'text-white'),
    ('text-slate-800', 'text-gray-200'),
    ('text-slate-700', 'text-gray-300'),
    ('text-slate-600', 'text-gray-400'),
    ('text-slate-500', 'text-gray-500'),
    ('text-slate-400', 'text-gray-400'),
    ('text-slate-300', 'text-gray-400'),
    ('border-slate-200', 'border-[#1e1e1e]'),
    ('hover:bg-slate-100', 'hover:bg-white/10'),
    ('bg-slate-100', 'bg-white/10'),
    ('bg-slate-50', 'bg-white/5'),
    ('slate-900/[0.06]', 'white/8'),
    ('slate-900/[0.04]', 'white/4'),
    ('slate-900/40', 'white/40'),
    ('slate-900/10', 'white/10'),
    ('slate-900/5', 'white/5'),
    ('#eaedf2', '#0a0a0a'),
    ('#e6e8ec', '#1e1e1e'),
    ('#d7dbe2', '#2a2a2a'),
    ('#d7dce4', '#2a2a2a'),
    ('#cbd2dc', '#2a2a2a'),
    ('#c2c9d4', '#2a2a2a'),
    ('#1c2230', '#e5e5e5'),
    ('#ffffff', '#141414'),
    ('rgba(15,23,42,', 'rgba(255,255,255,'),
]

base = pathlib.Path('.')
for rel in FILES:
    p = base / rel
    if not p.exists():
        continue
    txt = p.read_text(encoding='utf-8')
    orig = txt
    for a, b in REPL:
        if a.startswith(r'\b') or a.endswith(r'\b'):
            txt = re.sub(a, b, txt)
        else:
            txt = txt.replace(a, b)
    if txt != orig:
        p.write_text(txt, encoding='utf-8')
        print(f"darkened {rel}")
