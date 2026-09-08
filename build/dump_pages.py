import sys
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer
PDF='../GnGozbEwKKuzJeFZwlP44jd4P7XPAoUUz9lMqJEX.pdf'
pgs=[int(x) for x in sys.argv[1:]]
for pi,pl in enumerate(extract_pages(PDF, page_numbers=pgs)):
    real=pgs[pi]
    print(f'\n============ PDF PAGE {real} ============')
    rows=[]
    for el in pl:
        if isinstance(el, LTTextContainer):
            for ln in el:
                if hasattr(ln,'get_text'):
                    t=ln.get_text().rstrip('\n')
                    if t.strip():
                        rows.append((round(ln.x0),round(ln.y0),t.replace('\ufffd',"'")))
    rows.sort(key=lambda r:(-r[1], r[0]))
    for x0,y0,t in rows:
        print(f'x{x0:4d} y{y0:4d}| {t}')
