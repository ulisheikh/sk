from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime
import calendar
import os

async def create_calendar_image(workplace_name, month, year, work_dict, total_hours, gross, tax, net, hourly_rate, tax_rate):
    """Kalendar rasmini yaratish"""
    
    width, height = 900, 1500  # Balandlikni oshirdik
    img = Image.new('RGB', (width, height), color=(240, 248, 255))
    draw = ImageDraw.Draw(img)
    
    # Gradient fon
    for i in range(height):
        r = max(200, 240 - i//10)
        g = max(220, 248 - i//15)
        b = 255
        draw.line([(0, i), (width, i)], fill=(r, g, b))
    
    # SHRIFT YO'LINI TOPISH
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(current_file))
    font_dir = os.path.join(project_root, 'fonts')
    
    font_bold = os.path.join(font_dir, "NanumGothic-Bold.ttf")
    font_regular = os.path.join(font_dir, "NanumGothic-Regular.ttf")
    
    try:
        if os.path.exists(font_bold) and os.path.exists(font_regular):
            font_title = ImageFont.truetype(font_bold, 45)
            font_header = ImageFont.truetype(font_bold, 32)
            font_text = ImageFont.truetype(font_regular, 28)
            font_small = ImageFont.truetype(font_regular, 20)  # Shriftni kichiklashtirdik
        else:
            raise FileNotFoundError("Shrift fayllari topilmadi")
    except Exception as e:
        font_title = ImageFont.load_default()
        font_header = ImageFont.load_default()
        font_text = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Sarlavha
    draw.rounded_rectangle([(20, 20), (880, 140)], radius=15, fill=(65, 105, 225), outline=(0, 0, 139), width=3)
    draw.text((50, 40), f"🏢 {workplace_name}", fill=(255, 255, 255), font=font_title)
    draw.text((50, 95), f"📅 {year}년 {month}월", fill=(255, 255, 255), font=font_header)
    
    # Hafta kunlari
    draw.rounded_rectangle([(40, 170), (860, 220)], radius=10, fill=(100, 149, 237), outline=(70, 130, 180), width=2)
    
    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
    x_start = 70
    spacing = 110  # Kenglikni oshirdik
    
    for i, day in enumerate(weekday_names):
        x_pos = x_start + i * spacing
        draw.text((x_pos, 180), day, fill=(255, 255, 255), font=font_header)
    
    # Kalendar
    days_in_month = calendar.monthrange(year, month)[1]
    first_day = datetime(year, month, 1)
    start_weekday = first_day.weekday()
    
    y_pos = 250
    x_pos = x_start + start_weekday * spacing
    
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        hours = work_dict.get(date_str, None)
        
        # KATTAROQ KATAKCHALAR
        box_x1 = x_pos - 50
        box_y1 = y_pos - 10
        box_x2 = x_pos + 60
        box_y2 = y_pos + 110  # Balandlikni oshirdik
        
        if hours is not None:
            if hours == 0:
                draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=8, fill=(255, 200, 200), outline=(255, 100, 100), width=2)
            else:
                draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=8, fill=(200, 255, 200), outline=(100, 200, 100), width=2)
        else:
            draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=8, fill=(240, 240, 240), outline=(200, 200, 200), width=1)
        
        # Kun raqami
        day_text = str(day)
        bbox = draw.textbbox((0, 0), day_text, font=font_text)
        text_width = bbox[2] - bbox[0]
        draw.text((x_pos - text_width//2 + 5, y_pos + 5), day_text, fill=(0, 0, 0), font=font_text)
        
        # Soat yoki휴무
        if hours is not None:
            if hours == 0:
                휴무_bbox = draw.textbbox((0, 0), "휴무", font=font_text)
                휴무_width = 휴무_bbox[2] - 휴무_bbox[0]
                draw.text((x_pos - 휴무_width//2 + 5, y_pos + 50), "휴무", fill=(255, 0, 0), font=font_text)
            else:
                h_str = f"{hours}시간"
                h_bbox = draw.textbbox((0, 0), h_str, font=font_small)
                h_width = h_bbox[2] - h_bbox[0]
                draw.text((x_pos - h_width//2 + 5, y_pos + 55), h_str, fill=(0, 100, 0), font=font_small)
        
        date_obj = datetime(year, month, day)
        if date_obj.weekday() == 6:
            y_pos += 130  # Qator orasini oshirdik
            x_pos = x_start
        else:
            x_pos += spacing
    
    # Natija
    summary_y = y_pos + 130
    draw.rounded_rectangle([(40, summary_y), (860, summary_y + 220)], radius=15, fill=(255, 250, 205), outline=(255, 215, 0), width=3)
    
    draw.text((60, summary_y + 20), f"⏱️ 총 근무시간: {total_hours}시간", fill=(0, 0, 0), font=font_header)
    draw.text((60, summary_y + 65), f"💰 세전 급여: {gross:,.0f}원", fill=(0, 0, 0), font=font_text)
    draw.text((60, summary_y + 105), f"📉 세금 ({tax_rate}%): {tax:,.0f}원", fill=(139, 0, 0), font=font_text)
    draw.text((60, summary_y + 155), f"💵 실수령액: {net:,.0f}원", fill=(0, 100, 0), font=font_title)
    
    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    
    return bio