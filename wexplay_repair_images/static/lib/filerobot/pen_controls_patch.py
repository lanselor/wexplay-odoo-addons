"""Apply to pinned 4.8.1 after the two documented tool-list restrictions."""
from pathlib import Path
p = Path(__file__).with_name("filerobot-image-editor-4.8.1.min.js")
s = p.read_text(encoding="utf-8")
old = 'se.createElement(cj,{className:"FIE_pen-tool-options",annotation:l,updateAnnotation:s,t:e,hidePositionField:!0,hideFillOption:!0})'
new = 'se.createElement(wexPenControls,{annotation:l,updateAnnotation:c})'
control = 'function wexPenControls(e){var p=e.annotation,u=function(v){e.updateAnnotation(Object.assign({},v,{opacity:1,shadowBlur:0,shadowOpacity:0}))};return se.createElement("div",{className:"wex-pen-controls",role:"group","aria-label":"Pincel"},se.createElement("label",{className:"wex-pen-color"},"Color",se.createElement("input",{type:"color",value:p.stroke||"#ff0000","aria-label":"Color del pincel",onChange:function(e){u({stroke:e.target.value,fill:e.target.value})}})),se.createElement("label",{className:"wex-pen-width"},"Grosor",se.createElement("input",{type:"range",min:1,max:40,step:1,value:p.strokeWidth||4,"aria-label":"Grosor del pincel",onChange:function(e){u({strokeWidth:Number(e.target.value)})}}),se.createElement("output",null,(p.strokeWidth||4)+" px")))}'
assert s.count(old) == 1, "Unexpected bundle or patch already applied"
assert s.count('var hA="watermark"') == 1
s = s.replace(old, new).replace('var hA="watermark"', control + ';var hA="watermark"')
p.write_text(s, encoding="utf-8")
