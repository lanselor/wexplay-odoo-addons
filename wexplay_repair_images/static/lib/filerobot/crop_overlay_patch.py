"""Presentation-only opaque mask for pinned Filerobot 4.8.1 crop overlay."""
from pathlib import Path
p=Path(__file__).with_name("filerobot-image-editor-4.8.1.min.js")
s=p.read_text(encoding="utf-8")
old='se.createElement(jb,{image:f,x:g?h.width:0,y:m?h.height:0,width:h.width,height:h.height,filters:[eb.Filters.Blur,eb.Filters.Brighten],blurRadius:10,brightness:-.3,scaleX:g?-1:1,scaleY:m?-1:1,ref:C})'
new='se.createElement("Rect",{x:g?h.width:0,y:m?h.height:0,width:h.width,height:h.height,fill:u.palette["bg-secondary"],scaleX:g?-1:1,scaleY:m?-1:1,ref:C})'
assert s.count(old)==1, "Unexpected bundle or patch already applied"
p.write_text(s.replace(old,new),encoding="utf-8")
