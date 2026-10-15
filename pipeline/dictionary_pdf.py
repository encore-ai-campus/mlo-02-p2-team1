"""data/02_reference/standard_dictionary의 기준표로 표준사전 PDF를 만든다.

실행(저장소 루트): python -m pipeline.dictionary_pdf
"""
from pathlib import Path
import csv
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data' / '02_reference' / 'standard_dictionary'
OUT = SRC / 'F1_AI_data_standard_dictionary.pdf'
FONT = Path('C:/Windows/Fonts/malgun.ttf')
if FONT.exists(): pdfmetrics.registerFont(TTFont('Malgun', str(FONT)))
F = 'Malgun' if FONT.exists() else 'Helvetica'

def read(name):
    with (SRC / name).open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def para(v, style): return Paragraph(str(v).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'), style)
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleKR', parent=styles['Title'], fontName=F, fontSize=24, leading=30, textColor=colors.HexColor('#183B56'), alignment=1, spaceAfter=16))
styles.add(ParagraphStyle(name='H1KR', parent=styles['Heading1'], fontName=F, fontSize=18, leading=24, textColor=colors.HexColor('#183B56'), spaceBefore=12, spaceAfter=10))
styles.add(ParagraphStyle(name='H2KR', parent=styles['Heading2'], fontName=F, fontSize=15, leading=20, textColor=colors.HexColor('#2F6690'), spaceBefore=10, spaceAfter=7))
styles.add(ParagraphStyle(name='BodyKR', parent=styles['BodyText'], fontName=F, fontSize=15, leading=22))
styles.add(ParagraphStyle(name='CellKR', parent=styles['BodyText'], fontName=F, fontSize=10.5, leading=14))

def make_table(rows, cols, widths):
    body = [[para(v, styles['CellKR']) for v in row] for row in ([cols] + [[r.get(c,'') for c in cols] for r in rows])]
    t = Table(body, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#183B56')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#B8C7D3')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F3F7FA')]),('FONTNAME',(0,0),(-1,-1),F),('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
    return t
def footer(canvas, doc):
    canvas.saveState(); canvas.setFont(F, 9); canvas.setFillColor(colors.HexColor('#52606D')); canvas.drawString(50, 28, 'F1 AI 데이터 표준사전'); canvas.drawRightString(545, 28, str(doc.page)); canvas.restoreState()

doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50, title='F1 AI 데이터 표준사전')
story = [Spacer(1,25*mm), Paragraph('F1 AI 데이터 표준사전', styles['TitleKR']), Paragraph('오염 데이터 복구 및 품질 검증 파이프라인 기준', styles['BodyKR']), Spacer(1,10*mm), Paragraph('이 문서는 원본 명세서와 실제 진단 결과를 하나의 기준 문서로 통합합니다. 개발자는 컬럼과 허용값을 확인하고, 데이터 품질 담당자는 검증 규칙과 복구 관리값을 확인할 수 있습니다.', styles['BodyKR']), Spacer(1,8*mm), Paragraph('<b>문서 구성</b>　01 표준단어　02 표준용어　03 도메인　04 허용 코드　05 컬럼 표준사전　06 표준 조합 규칙', styles['BodyKR']), Spacer(1,5*mm), Paragraph('<b>진단 반영</b>　복구 기록 25,562건　검증 이슈 371건　명세서 확인 완료', styles['BodyKR']), PageBreak()]
sections = [('1. 표준단어','standard_words.csv',['word_id','standard_word','korean_name','definition','word_type'],[14*mm,22*mm,22*mm,94*mm,23*mm]),('2. 표준용어','standard_terms.csv',['term_id','standard_term','korean_term','definition','term_pattern','identifier_rule'],[12*mm,22*mm,22*mm,55*mm,26*mm,38*mm]),('3. 도메인','domains.csv',['domain_id','domain_name','korean_name','base_type','length_rule','unit','nullable','validation_rule'],[12*mm,25*mm,25*mm,18*mm,20*mm,16*mm,14*mm,45*mm]),('4. 허용 코드','codes.csv',['code_group','code','korean_name','description','active'],[22*mm,25*mm,25*mm,88*mm,15*mm]),('5. 오염 진단 코드','diagnostic_codes.csv',['diagnostic_code','diagnostic_name','korean_name','applies_to','condition','default_action','default_confidence'],[17*mm,28*mm,27*mm,38*mm,40*mm,60*mm,25*mm])]
for title, name, cols, widths in sections:
    story += [Paragraph(title, styles['H1KR']), make_table(read(name), cols, widths), PageBreak()]
cols = ['file_name','column_name','standard_term','data_type','length','nullable','unit','domain','allowed_values','validation_rule']
story += [Paragraph('6. 컬럼 표준사전', styles['H1KR']), Paragraph('컬럼별 상세 규칙을 읽기 쉬운 카드형 표로 정리했습니다. 타입은 원본 보존 기준이며, 계산 시에만 숫자나 날짜로 해석합니다.', styles['BodyKR'])]
short_cols = ['column_name','standard_term','data_type','length','nullable','unit','domain','allowed_values','validation_rule']
short_widths = [28*mm,32*mm,22*mm,18*mm,16*mm,18*mm,31*mm,63*mm,63*mm]
for file_name in ['sessions.csv','drivers.csv','laps.csv','pit.csv','stints.csv','weather.csv']:
    story.append(Paragraph(file_name, styles['H2KR']))
    for r in [r for r in read('column_dictionary.csv') if r['file_name'] == file_name]:
        card = [['컬럼', r['column_name'], '표준용어', r['standard_term']], ['타입/길이', r['data_type']+' / '+r['length'], '결측/단위', r['nullable']+' / '+(r['unit'] or '-')], ['도메인', r['domain'], '허용값', r['allowed_values'] or '-'], ['검증 규칙', r['validation_rule'], '', '']]
        t = Table([[para(v, styles['CellKR']) for v in row] for row in card], colWidths=[22*mm,45*mm,22*mm,86*mm])
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#EAF1F6')),('BACKGROUND',(2,0),(2,-2),colors.HexColor('#EAF1F6')),('SPAN',(1,3),(3,3)),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#B8C7D3')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        story += [t, Spacer(1, 3*mm)]
story += [PageBreak(), Paragraph('7. 표준 조합 규칙', styles['H1KR'])]
for line in (SRC/'composition_rules.md').read_text(encoding='utf-8').splitlines():
    if line.startswith('# '): continue
    if line.startswith('## '): story.append(Paragraph(line[3:], styles['H2KR']))
    elif line.startswith('- '): story.append(Paragraph('• '+line[2:], styles['BodyKR']))
    elif line.strip(): story.append(Paragraph(line, styles['BodyKR']))
    story.append(Spacer(1,1.2*mm))
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
