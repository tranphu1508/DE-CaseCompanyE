"""Render the CompanyE enterprise bus matrix in the CO5173 slide 89 style."""
import json
import math
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, black, white
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'config/dimensional_model_v1.json'
OUTPUT = ROOT / 'docs/CompanyE_Bus_Matrix.pdf'
model = json.loads(MODEL.read_text(encoding='utf-8'))
processes = model['enterprise_bus_matrix']['processes']
dimensions = model['dimensions']
assert len(processes) == 12 and len(dimensions) == 16

for name, file in [('Arial', 'arial.ttf'), ('Arial-Bold', 'arialbd.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(Path('C:/Windows/Fonts') / file)))

labels = ['Ngày', 'Cụm', 'Khách sạn', 'Phòng', 'Kênh bán', 'Khuyến mãi',
          'Hồ sơ khách', 'Gói giá', 'Điểm ăn uống', 'Bữa ăn', 'Trung tâm',
          'Hoạt động', 'Phương tiện', 'Nhà cung cấp', 'Mặt hàng', 'Tài sản']

W, H = 1200, 900
c = canvas.Canvas(str(OUTPUT), pagesize=(W, H), pageCompression=1)
c.setTitle('CompanyE - Bus matrix tổng quan')
c.setAuthor('CompanyE Project - CO5173')
c.setSubject('12 quá trình nghiệp vụ và 16 dimension; trình bày theo mẫu slide 89')
c.setFillColor(white)
c.rect(0, 0, W, H, stroke=0, fill=1)

# Match the course slide's white background, blue heading and left colour strip.
for bottom, height, color in [(600, 300, '#090477'), (300, 300, '#073478'), (0, 300, '#0F53DD')]:
    c.setFillColor(HexColor(color))
    c.rect(0, bottom, 25, height, stroke=0, fill=1)
c.setFillColor(HexColor('#0800C7'))
c.setFont('Arial', 40)
c.drawString(65, 831, 'CompanyE - Bus matrix tổng quan')
c.setStrokeColor(HexColor('#0800C7'))
c.setLineWidth(1.2)
c.line(40, 810, 1170, 810)
c.setFillColor(HexColor('#333333'))
c.setFont('Arial', 15)
c.drawString(65, 778, 'Mô hình logic theo Kimball | 12 quá trình nghiệp vụ - 16 dimension dùng chung')

# Angled parallelogram column headings, as in Figure 5.1 on the course slide.
x, y = 65, 207
label_w, cell_w, row_h = 275, 46, 30
body_h, header_h, skew = len(processes) * row_h, 170, 62
top = y + body_h
start = x + label_w
right = start + len(dimensions) * cell_w
c.setStrokeColor(black)
c.setLineWidth(0.8)
c.rect(x, y, right - x, body_h, stroke=1, fill=0)
for i in range(1, len(processes)):
    yy = y + i * row_h
    c.line(x, yy, right, yy)
for j in range(len(dimensions) + 1):
    xx = start + j * cell_w
    c.line(xx, y, xx, top)
    c.line(xx, top, xx + skew, top + header_h)
c.line(start + skew, top + header_h, right + skew, top + header_h)

angle = math.degrees(math.atan2(header_h, skew))
c.setFillColor(black)
for j, (dim, label) in enumerate(zip(dimensions, labels)):
    c.saveState()
    c.translate(start + (j + 0.5) * cell_w + 2, top + 12)
    c.rotate(angle)
    c.setFont('Arial', 15)
    title = f"{dim['id']}  {label}"
    assert pdfmetrics.stringWidth(title, 'Arial', 15) < math.hypot(skew, header_h) - 16
    c.drawString(0, -4, title)
    c.restoreState()

marked_cells = 0
for i, process in enumerate(processes):
    baseline = top - (i + 0.5) * row_h - 5
    text = f"{process['id']}  {process['name']}"
    c.setFont('Arial', 13)
    assert pdfmetrics.stringWidth(text, 'Arial', 13) < label_w - 16
    c.drawString(x + 9, baseline, text)
    for j, dim in enumerate(dimensions):
        if dim['id'] in process['dimensions']:
            c.setFont('Arial-Bold', 18)
            c.drawCentredString(start + (j + 0.5) * cell_w, baseline - 1, 'X')
            marked_cells += 1

c.setFont('Arial-Bold', 14)
c.drawString(65, 704, 'QUÁ TRÌNH NGHIỆP VỤ')
c.setFont('Arial', 13)
c.drawString(65, 681, 'Hàng: quá trình phát sinh dữ liệu')
c.drawString(65, 661, 'Cột nghiêng: dimension liên quan')
c.drawString(65, 641, 'X: sử dụng trong quá trình')
c.drawString(65, 621, 'Ô trống: không dùng trong thiết kế')

c.setFont('Arial-Bold', 15)
c.drawString(65, 177, 'Hình 1.')
c.setFont('Arial', 15)
c.drawString(121, 177, 'Bus matrix tổng quan cho các quá trình nghiệp vụ của CompanyE trong phạm vi B01-B08.')
notes = [
    'Một dấu X biểu thị quan hệ ở cấp quá trình; không có nghĩa mọi fact hoặc KPI trong quá trình đều nhận bộ lọc đó.',
    'D07 là hồ sơ khách theo từng nguồn, chưa hợp nhất khách. D04/D08 ở P01 liên kết qua BridgeBookingRoom.',
    'F15 (tồn kho theo ngày) là tổng hợp tùy chọn thuộc P11. F17 (thời tiết) là dữ liệu ngữ cảnh, không là hàng nghiệp vụ riêng.',
]
c.setFillColor(HexColor('#333333'))
c.setFont('Arial', 12)
for i, note in enumerate(notes):
    c.drawString(65, 147 - i * 20, note)
c.setFont('Arial', 11)
c.drawString(65, 66, 'Mẫu trình bày: CO5173, Chương 2 - Data Warehouse and Data Management Architecture Design, slide 89, Figure 5.1.')
c.drawString(65, 48, 'Tham chiếu mẫu: Kimball & Ross, The Data Warehouse Toolkit, 2nd ed., 2002. Nội dung ma trận: thiết kế CompanyE v1.0.')
c.drawRightString(1170, 25, '1')
c.showPage()
c.save()

# Confirm embedded Vietnamese text and every matrix mark survived PDF output.
reader = PdfReader(OUTPUT)
assert len(reader.pages) == 1
text = reader.pages[0].extract_text()
for process in processes:
    assert process['name'] in text
for dim in dimensions:
    assert dim['id'] in text
assert sum(line.strip() == 'X' for line in text.splitlines()) == marked_cells
print(json.dumps({'output': str(OUTPUT), 'pages': 1, 'processes': 12,
                  'dimensions': 16, 'marked_cells': marked_cells,
                  'validation': 'PASSED'}, ensure_ascii=True))
