from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime
import calendar
import os

async def create_calendar_image(workplace_name, month, year, work_dict, total_hours, gross, tax, net, hourly_rate, tax_rate, first_name=None, last_name=None):
    """Kalendar rasmini yaratish (Ism ishxona bilan bir qatorda, o'ngda)"""
    
    full_name_parts = [part for part in [first_name, last_name] if part]
    display_name = " ".join(full_name_parts) if full_name_parts else "Foydalanuvchi"
    
    width, height = 900, 1500
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
            font_name = ImageFont.truetype(font_regular, 26) 
            font_text = ImageFont.truetype(font_regular, 28)
            font_small = ImageFont.truetype(font_regular, 20)
        else:
            raise FileNotFoundError("Shrift fayllari topilmadi")
    except Exception:
        font_title = font_header = font_name = font_text = font_small = ImageFont.load_default()
    
    # Sarlavha qutisi
    draw.rounded_rectangle([(20, 20), (880, 165)], radius=15, fill=(65, 105, 225), outline=(0, 0, 139), width=3)
    
    # 1. Ishxona nomi (Chapda)
    draw.text((60, 45), f"🏢 {workplace_name}", fill=(255, 255, 255), font=font_title)
    
    # 2. Foydalanuvchi ismi (Ishxona bilan bir qatorda, lekin O'NGDA)
    name_text = f"👤 {display_name}"
    name_bbox = draw.textbbox((0, 0), name_text, font=font_name)
    name_width = name_bbox[2] - name_bbox[0]
    # O'ng tomondan 60px masofada taqash
    draw.text((840 - name_width, 60), name_text, fill=(220, 220, 220), font=font_name)
    
    # 3. Sana (Pastki qatorda)
    draw.text((60, 115), f"📅 {year}년 {month}월", fill=(255, 255, 255), font=font_header)
    
    # Hafta kunlari
    draw.rounded_rectangle([(40, 185), (860, 235)], radius=10, fill=(100, 149, 237), outline=(70, 130, 180), width=2)
    
    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
    x_start = 70
    spacing = 110
    
    for i, day in enumerate(weekday_names):
        x_pos = x_start + i * spacing
        draw.text((x_pos, 195), day, fill=(255, 255, 255), font=font_header)
    
    # Kalendar kunlari mantiqi
    days_in_month = calendar.monthrange(year, month)[1]
    first_day = datetime(year, month, 1)
    start_weekday = first_day.weekday()
    
    y_pos = 265
    x_pos = x_start + start_weekday * spacing
    
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        hours = work_dict.get(date_str, None)
        
        box_x1, box_y1 = x_pos - 50, y_pos - 10
        box_x2, box_y2 = x_pos + 60, y_pos + 110
        
        if hours is not None:
            color = (200, 255, 200) if hours > 0 else (255, 200, 200)
            outline = (100, 200, 100) if hours > 0 else (255, 100, 100)
            draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=8, fill=color, outline=outline, width=2)
        else:
            draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=8, fill=(240, 240, 240), outline=(200, 200, 200), width=1)
        
        day_text = str(day)
        bbox = draw.textbbox((0, 0), day_text, font=font_text)
        draw.text((x_pos - (bbox[2]-bbox[0])//2 + 5, y_pos + 5), day_text, fill=(0, 0, 0), font=font_text)
        
        if hours is not None:
            txt = "휴무" if hours == 0 else f"{hours}h"
            fnt = font_text if hours == 0 else font_small
            clr = (255, 0, 0) if hours == 0 else (0, 100, 0)
            t_bbox = draw.textbbox((0, 0), txt, font=fnt)
            draw.text((x_pos - (t_bbox[2]-t_bbox[0])//2 + 5, y_pos + 55), txt, fill=clr, font=fnt)
        
        if datetime(year, month, day).weekday() == 6:
            y_pos += 130
            x_pos = x_start
        else:
            x_pos += spacing
    
    # Summary qismi
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