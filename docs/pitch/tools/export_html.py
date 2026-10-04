"""Bundle the built slides into ONE offline HTML file you can present and record.

No network, no fonts to download, no libraries: arrow keys / space / click to
move, F for full screen, the 1920x1080 stage scales to the window. Speaker notes
stay in the file but are hidden.
"""
import json
import os

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>
html,body{{margin:0;height:100%;background:#111;overflow:hidden}}
#stage{{position:absolute;left:50%;top:50%;width:1920px;height:1080px;transform-origin:0 0}}
section{{position:absolute;inset:0;box-sizing:border-box;width:1920px;height:1080px;overflow:hidden;display:none}}
section.on{{display:flex}} section *{{margin:0;box-sizing:border-box}} aside{{display:none}}
table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #D3D2D2;text-align:left}}
#n{{position:fixed;right:12px;bottom:8px;font:14px sans-serif;color:#888}}
</style></head><body><div id="stage">{body}</div><div id="n"></div>
<script>
const s=[...document.querySelectorAll('section')],st=document.getElementById('stage');let i=0;
function fit(){{const k=Math.min(innerWidth/1920,innerHeight/1080);st.style.transform=`scale(${{k}}) translate(-50%,-50%)`;}}
function go(j){{i=Math.max(0,Math.min(s.length-1,j));s.forEach((e,k)=>e.classList.toggle('on',k===i));
document.getElementById('n').textContent=(i+1)+' / '+s.length;history.replaceState(null,'','#'+(i+1));}}
addEventListener('keydown',e=>{{if(['ArrowRight','PageDown',' '].includes(e.key))go(i+1);
if(['ArrowLeft','PageUp'].includes(e.key))go(i-1);if(e.key==='f')document.documentElement.requestFullscreen();}});
addEventListener('click',()=>go(i+1));addEventListener('resize',fit);fit();go((parseInt(location.hash.slice(1))||1)-1);
</script></body></html>"""


def export(out_dir, dest):
    proj = os.path.join(out_dir, "project")
    index = json.load(open(os.path.join(proj, "deck.json"), encoding="utf-8"))
    body = "\n".join(open(os.path.join(proj, "slides", sid + ".html"), encoding="utf-8").read()
                     for sid in index["order"])
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(PAGE.format(title=index["title"], body=body))
    return dest
