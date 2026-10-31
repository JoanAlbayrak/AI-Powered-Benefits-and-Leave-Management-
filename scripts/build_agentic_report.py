"""Build the illustrated proposal from its editable Markdown source.

Requires reportlab. Run from the repository root. No network or model calls.
"""
from pathlib import Path
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, Flowable

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/BENEFITS-LEAVE-PROPOSAL.md"
OUTPUT = ROOT / "outputs/Benefits-and-Leave-Case-Team-Report.pdf"
W, H = 612, 792
INK, TEAL = colors.HexColor('#172D42'), colors.HexColor('#087F83')
MUTED, PAPER = colors.HexColor('#526577'), colors.HexColor('#FAFBFC')
LINE, PALE = colors.HexColor('#D8E2E8'), colors.HexColor('#EDF5F5')
URLS = {
    int(n): url for n, url in re.findall(
        r'### \[(\d+)\][^\n]*\n.*?\nLINK: (\S+)', SOURCE.read_text(), re.S)
}


def rich(s):
    s = escape(s)
    return re.sub(r'\[(\d+)\]', lambda m: (
        f'<link href="{escape(URLS[int(m[1])])}" color="#087F83">[{m[1]}]</link>'
        if int(m[1]) in URLS else m[0]), s)


class Journey(Flowable):
    def __init__(self, labels):
        super().__init__()
        self.labels, self.width, self.height = labels, 516, 83

    def draw(self):
        c = self.canv
        cell = self.width / len(self.labels)
        c.setStrokeColor(LINE)
        c.line(cell / 2, 63, self.width - cell / 2, 63)
        for i, label in enumerate(self.labels):
            x = cell * (i + .5)
            c.setFillColor(TEAL)
            c.circle(x, 63, 11, stroke=0, fill=1)
            c.setFillColor(colors.white)
            c.setFont('Helvetica-Bold', 9)
            c.drawCentredString(x, 60, str(i + 1))
            p = Paragraph(rich(label), ParagraphStyle(
                'journey', fontName='Helvetica-Bold', fontSize=9.2,
                leading=12, alignment=1, textColor=INK))
            _, ph = p.wrap(cell - 12, 48)
            p.drawOn(c, cell * i + 6, 42 - ph)


def styles(size):
    return {
        'body': ParagraphStyle('body', fontName='Helvetica', fontSize=size,
            leading=size * 1.43, textColor=INK, spaceAfter=7),
        'heading': ParagraphStyle('heading', fontName='Helvetica-Bold',
            fontSize=size + 1.1, leading=size * 1.4, textColor=TEAL,
            spaceBefore=5, spaceAfter=5),
        'bullet': ParagraphStyle('bullet', fontName='Helvetica', fontSize=size,
            leading=size * 1.4, textColor=INK, leftIndent=12,
            firstLineIndent=-10, spaceAfter=5),
        'quote': ParagraphStyle('quote', fontName='Helvetica-Bold',
            fontSize=size + .2, leading=size * 1.45, textColor=INK,
            backColor=PALE, borderPadding=11, spaceBefore=10, spaceAfter=18),
        'link': ParagraphStyle('link', fontName='Helvetica', fontSize=size - .8,
            leading=size * 1.3, textColor=TEAL, spaceAfter=7),
        'table': ParagraphStyle('table', fontName='Helvetica', fontSize=size - .7,
            leading=size * 1.3, textColor=INK),
        'th': ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=size - .7,
            leading=size * 1.3, textColor=colors.white),
    }


def blocks(lines, size):
    st = styles(size)
    result, i = [], 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if s.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append([v.strip() for v in lines[i].strip().strip('|').split('|')])
                i += 1
            ncols = len(rows[0])
            widths = {2: [159, 357], 3: [142, 182, 192]}[ncols]
            data = [[Paragraph(rich(cell), st['th' if j == 0 else 'table'])
                for cell in row] for j, row in enumerate(rows)]
            table = Table(data, colWidths=widths, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), INK),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, PAPER]),
                ('LINEBELOW', (0, 0), (-1, -1), .4, LINE),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            result.extend([table, Spacer(1, 11)])
            continue
        if s.startswith('FLOW: '):
            result.append(Journey(s[6:].split(' | ')))
        elif s.startswith('### '):
            result.append(Paragraph(rich(s[4:]), st['heading']))
        elif s.startswith('> '):
            result.append(Paragraph(rich(s[2:]), st['quote']))
        elif s.startswith('- '):
            result.append(Paragraph('&#8226; ' + rich(s[2:]), st['bullet']))
        elif s.startswith('LINK: '):
            url = s[6:]
            domain = url.split('/')[2]
            result.append(Paragraph(
                f'<link href="{escape(url)}" color="#087F83">Open source / {domain}</link>', st['link']))
        else:
            result.append(Paragraph(rich(s), st['body']))
        i += 1
    return result


def height(items):
    return sum(item.getSpaceBefore() + item.wrap(516, 900)[1] +
        item.getSpaceAfter() for item in items)


def chrome(c, page, count):
    c.setFillColor(PAPER)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(0, H - 7, W, 7, fill=1, stroke=0)
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(MUTED)
    c.drawString(48, H - 35, 'BENEFITS & LEAVE / CASE TEAM')
    c.setFont('Helvetica', 8)
    c.drawRightString(564, H - 35, 'FIELD GUIDE + PRODUCT PROPOSAL')
    c.setStrokeColor(LINE)
    c.line(48, 45, 564, 45)
    c.setFont('Helvetica', 8)
    c.drawString(48, 29, '31 OCT 2026  /  U.S. CONTEXT  /  PROPOSED FEATURES LABELED')
    c.drawRightString(564, 29, f'{page:02d} / {count:02d}')


def main():
    pages = SOURCE.read_text().split('\n---\n')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    c = Canvas(str(OUTPUT), pagesize=(W, H))
    c.setTitle('Benefits & Leave Case Team - Field Guide and Proposal')
    c.setAuthor('Joan Albayrak and Dikshyant Giri')
    diagnostics = []
    for num, page in enumerate(pages, 1):
        lines = page.strip().splitlines()
        title = lines.pop(0).removeprefix('# ')
        subtitle = lines.pop(0).removeprefix('## ')
        chrome(c, num, len(pages))
        c.bookmarkPage(f'page-{num}')
        c.addOutlineEntry(title, f'page-{num}', level=0)
        if num == 1:
            c.setFillColor(TEAL)
            c.setFont('Helvetica-Bold', 10)
            c.drawString(48, 708, 'THREE SPECIALISTS. ONE CLEAR CASE.')
            t = Paragraph('Benefits &amp; Leave<br/>Case Team', ParagraphStyle(
                'cover', fontName='Helvetica-Bold', fontSize=39, leading=43,
                textColor=INK))
            _, th = t.wrap(516, 110)
            t.drawOn(c, 48, 688 - th)
            c.setFont('Helvetica', 15)
            c.setFillColor(MUTED)
            c.drawString(48, 570, subtitle)
            y = 539
        else:
            c.setFont('Helvetica-Bold', 18)
            c.setFillColor(INK)
            c.drawString(48, 704, title)
            p = Paragraph(rich(subtitle), ParagraphStyle('sub', fontName='Helvetica',
                fontSize=15, leading=20, textColor=MUTED))
            _, ph = p.wrap(516, 55)
            p.drawOn(c, 48, 676 - ph)
            y = 665 - ph
        available = y - 64
        for size in [10.5, 10.2, 9.9, 9.6, 9.3]:
            items = blocks(lines, size)
            used = height(items)
            if used <= available:
                break
        if used > available:
            raise RuntimeError(f'Page {num} overflows: {used:.1f} > {available:.1f}')
        for item in items:
            y -= item.getSpaceBefore()
            _, h = item.wrap(516, 900)
            y -= h
            item.drawOn(c, 48, y)
            y -= item.getSpaceAfter()
        diagnostics.append(f'Page {num:02d}: font {size}; content {used:.0f}/{available:.0f} pt; bottom {y:.0f}')
        c.showPage()
    c.save()
    print('\n'.join(diagnostics))
    print(OUTPUT)


if __name__ == '__main__':
    main()
