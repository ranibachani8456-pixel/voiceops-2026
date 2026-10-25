from pathlib import Path
import html
import re
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
root=Path(__file__).resolve().parents[1]
styles=getSampleStyleSheet();styles['Title'].textColor=colors.HexColor('#6550a4');styles['BodyText'].fontSize=10;styles['BodyText'].leading=15
story=[]
for block in (root/'report/technical_report.md').read_text().split('\n\n'):
    block=block.strip()
    if not block:continue
    if block.startswith('# '):style=styles['Title'];block=block[2:]
    elif block.startswith('## '):style=styles['Heading2'];block=block[3:]
    else:style=styles['BodyText']
    rendered = html.escape(block).replace('\n','<br/>')
    rendered = re.sub(r'\[([^\]]+)\]\((https://[^)\s]+)\)', r'<link href="\2" color="#6550a4">\1</link>', rendered)
    spacer = Spacer(1,8)
    spacer.keepWithNext = style in (styles['Title'], styles['Heading2'])
    story.extend([Paragraph(rendered,style),spacer])
def footer(canvas,doc):
    canvas.setFont('Helvetica',8);canvas.setFillColor(colors.grey);canvas.drawString(42,25,'VOICEOPS 2026 | Implementation report | 25 October 2026');canvas.drawRightString(550,25,str(doc.page))
SimpleDocTemplate(str(root/'report/report.pdf'),rightMargin=42,leftMargin=42,topMargin=40,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
