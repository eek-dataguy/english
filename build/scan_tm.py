from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer
import re, pickle, sys

PDF='../GnGozbEwKKuzJeFZwlP44jd4P7XPAoUUz9lMqJEX.pdf'

def page_lines(pl):
    out=[]
    for el in pl:
        if isinstance(el, LTTextContainer):
            for ln in el:
                if hasattr(ln,'get_text'):
                    t=ln.get_text().rstrip('\n')
                    if t.strip():
                        out.append((ln.x0, ln.y0, ln.x1, t))
    return out

hits=[]
for pi,pl in enumerate(extract_pages(PDF)):
    L=page_lines(pl)
    for x0,y0,x1,t in L:
        tt=re.sub(r'\s+',' ',t).strip()
        if re.search(r'\b(ELEMENTARY|PRE-?INTERMEDIATE|INTERMEDIATE|UPPER-?INTERMEDIATE|ADVANCED)\b', tt) and ('TEST' in tt.upper() or len(tt)<40):
            hits.append((pi,round(x0),round(y0),tt[:70]))
        if re.match(r'PART\s+[A-E]\b', tt) or re.match(r'BOOK\s+\d', tt) or 'ANSWER KEY' in tt.upper():
            hits.append((pi,round(x0),round(y0),'>>> '+tt[:70]))
for h in hits:
    print(h)
