"""Build a portable offline HTML from this folder's snapshot and UI sources."""
from pathlib import Path
import json
BASE=Path(__file__).resolve().parent
data=json.loads((BASE/'data.json').read_text(encoding='utf-8'))
template=(BASE/'template.html').read_text(encoding='utf-8')
app=(BASE/'app.js').read_text(encoding='utf-8')
app=(BASE/'story.js').read_text(encoding='utf-8')+'\n'+app
app=(BASE/'candidates.js').read_text(encoding='utf-8')+'\n'+app
app=(BASE/'trust.js').read_text(encoding='utf-8')+'\n'+app
app=(BASE/'operations.js').read_text(encoding='utf-8')+'\n'+app
template=template.replace('<style>','<style>\n'+(BASE/'story.css').read_text(encoding='utf-8')+'\n',1)
template=template.replace('</style>','\n'+(BASE/'candidates.css').read_text(encoding='utf-8')+'\n</style>',1)
template=template.replace('</style>','\n'+(BASE/'trust.css').read_text(encoding='utf-8')+'\n</style>',1)
template=template.replace('</style>','\n'+(BASE/'operations.css').read_text(encoding='utf-8')+'\n</style>',1)
snapshot=json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False).replace('<','\\u003c')
out=BASE/'dist';out.mkdir(exist_ok=True)
html=template.replace('__DATA__',snapshot).replace('__APP__',app)
(out/'index.html').write_text(html,encoding='utf-8')
(BASE/'F1_decision_board_test.html').write_text(html,encoding='utf-8')
print(f'Built {out / "index.html"} ({len(html.encode("utf-8")):,} bytes)')
