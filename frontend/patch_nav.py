#!/usr/bin/env python3
"""
Jacquard Loom — nav replacer v4
Completely replaces the <nav>...</nav> block in each screen.
Run from ~/weave/frontend/:  python3 patch_nav.py
"""
import os, re

# ── SHARED NAV PIECES ──

LOGO = '''  <a class="nav-logo" href="screen1-build.html">
    <svg width="40" height="24" viewBox="0 0 140 100">
      <path d="M0 50 C23 0, 47 0, 70 50 C93 100, 117 100, 140 50" fill="none" stroke="#63DF4E" stroke-width="8" stroke-linecap="round"/>
      <path d="M0 50 C23 100, 47 100, 70 50 C93 0, 117 0, 140 50" fill="none" stroke="#A8C8DC" stroke-width="8" stroke-linecap="round"/>
    </svg>
    Jacquard Loom
  </a>'''

PERSONA = '''  <div class="persona-wrapper">
    <span class="persona-static-label">Persona:</span>
    <div class="persona-dropdown" id="persona-dropdown" onclick="togglePersonaMenu(event)">
      <span>AI Admin</span>
      <svg class="persona-chevron" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="2,4 6,8 10,4"/>
      </svg>
      <div class="persona-menu" onclick="event.stopPropagation()">
        <div class="persona-menu-item current"><span class="persona-dot admin"></span>AI Admin</div>
        <div class="persona-menu-divider"></div>
        <div class="persona-menu-item" onclick="window.location.href='screen7-fulfiller.html'">
          <span class="persona-dot fulfiller"></span>Fulfiller
        </div>
      </div>
    </div>
  </div>'''

def std_nav(active):
    links = ['Build','Library','Tools']
    buttons = '\n'.join(
        f'    <button class="nav-link{\" active\" if l==active else \"\"}" onclick="window.location.href=\'screen{[\"Build\":1,\"Library\":4,\"Tools\":5][l]}-{l.lower()}.html\'">{l}</button>'
        for l in links
    )
    # Simpler approach
    build_cls   = ' active' if active == 'Build'   else ''
    library_cls = ' active' if active == 'Library' else ''
    tools_cls   = ' active' if active == 'Tools'   else ''
    nav_links = f'''  <div class="nav-links">
    <button class="nav-link{build_cls}" onclick="window.location.href='screen1-build.html'">Build</button>
    <button class="nav-link{library_cls}" onclick="window.location.href='screen4-library.html'">Library</button>
    <button class="nav-link{tools_cls}" onclick="window.location.href='screen5-tools.html'">Tools</button>
  </div>'''
    return f'<nav>\n{LOGO}\n{nav_links}\n{PERSONA}\n</nav>'

STEP_SEP = '  <div class="step-sep"></div>'

def step(num, label, state):
    if state == 'done':
        cls = 'nav-step done'
        inner = '<div class="step-num">✓</div>'
    elif state == 'active':
        cls = 'nav-step active'
        inner = f'<div class="step-num">{num}</div>'
    else:
        cls = 'nav-step'
        inner = f'<div class="step-num">{num}</div>'
    return f'  <div class="{cls}">{inner}{label}</div>'

def stepper_nav(s1, s2, s3, wf_badge=True):
    stepper = f'''  <div class="nav-stepper">
{step(1,"Build",s1)}
{STEP_SEP}
{step(2,"Validate",s2)}
{STEP_SEP}
{step(3,"Execute",s3)}
  </div>'''
    wf = '  <div class="nav-wf">Workflow&nbsp;<span class="wf-badge" id="wf-id-display">—</span></div>'
    return f'<nav>\n{LOGO}\n{stepper}\n{wf}\n{PERSONA}\n</nav>'

PERSONA_CSS = """
/* ── PERSONA SWITCHER ── */
nav { overflow: visible !important; }
.persona-wrapper { display: flex; align-items: center; gap: 8px; }
.persona-static-label { font-size: 12px; color: var(--text-muted); white-space: nowrap; user-select: none; }
.persona-dropdown {
  position: relative; display: flex; align-items: center; gap: 7px;
  background: var(--surface-2); border: 1px solid var(--border-subtle);
  border-radius: 8px; padding: 6px 12px;
  font-size: 12px; font-weight: 600; color: var(--text-primary);
  cursor: pointer; user-select: none; transition: border-color 0.15s;
}
.persona-dropdown:hover { border-color: var(--border-mid); }
.persona-dropdown.open  { border-color: var(--border-green); }
.persona-chevron { color: var(--text-muted); transition: transform 0.2s; flex-shrink: 0; }
.persona-dropdown.open .persona-chevron { transform: rotate(180deg); }
.persona-menu {
  display: none; position: absolute; top: calc(100% + 8px); right: 0;
  background: var(--surface-2); border: 1px solid var(--border-mid);
  border-radius: 10px; padding: 6px; min-width: 180px; z-index: 9999;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}
.persona-dropdown.open .persona-menu { display: block; }
.persona-menu-item {
  display: flex; align-items: center; gap: 10px; padding: 9px 12px;
  border-radius: 7px; font-size: 13px; font-weight: 500; color: var(--text-secondary);
  cursor: pointer; transition: background 0.12s; white-space: nowrap;
}
.persona-menu-item:hover { background: var(--surface-3); color: var(--text-primary); }
.persona-menu-item.current { color: var(--wasabi-green); pointer-events: none; }
.persona-menu-divider { height: 1px; background: var(--border-subtle); margin: 4px 0; }
.persona-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.persona-dot.admin     { background: var(--bright-blue); }
.persona-dot.fulfiller { background: var(--wasabi-green); }"""

PERSONA_JS = """
// ── PERSONA SWITCHER ──
function togglePersonaMenu(e) {
  e.stopPropagation();
  var dd = document.getElementById('persona-dropdown');
  if (dd) dd.classList.toggle('open');
}
document.addEventListener('click', function() {
  var dd = document.getElementById('persona-dropdown');
  if (dd) dd.classList.remove('open');
});"""

# Map each screen to its correct nav
NAV_MAP = {
    'screen1-build.html':   std_nav('Build'),
    'screen2-validate.html': stepper_nav('done','active',''),
    'screen3-execute.html':  stepper_nav('done','done','active'),
    'screen4-library.html':  std_nav('Library'),
    'screen5-tools.html':    std_nav('Tools'),
    'screen6-sandbox.html':  std_nav(''),
}

def patch_file(filename, new_nav):
    if not os.path.exists(filename):
        print(f'  SKIP     {filename} (not found)')
        return

    with open(filename, 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Replace entire <nav>...</nav> block
    html = re.sub(r'<nav>.*?</nav>', new_nav, html, count=1, flags=re.DOTALL)

    # 2. Remove any leftover persona CSS/HTML/JS from old patches
    html = re.sub(r'/\* ── PERSONA SWITCHER ──.*?(?=\n\.)', '', html, flags=re.DOTALL)

    # 3. Inject fresh persona CSS before last </style>
    if 'persona-dropdown' not in html:
        pos = html.rfind('</style>')
        if pos != -1:
            html = html[:pos] + PERSONA_CSS + '\n</style>' + html[pos+8:]

    # 4. Inject fresh persona JS before last </script>
    if 'togglePersonaMenu' not in html:
        pos = html.rfind('</script>')
        if pos != -1:
            html = html[:pos] + PERSONA_JS + '\n</script>' + html[pos+9:]

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  PATCHED  {filename}')

if __name__ == '__main__':
    print('Jacquard Loom — nav replacer v4\n')
    for filename, nav in NAV_MAP.items():
        patch_file(filename, nav)
    print('\nDone. Hard-refresh browser with Cmd+Shift+R')
