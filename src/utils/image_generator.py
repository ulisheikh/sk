from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime
import calendar
import os
import asyncio

async def create_calendar_image(workplace_name, month, year, work_dict, total_hours, gross, tax, net, hourly_rate, tax_rate):
    """Kalendar rasmini yaratish"""
    
    # Rasm o'lchami
    width, height = 900, 1400
    
    # Fon rangi (och ko'k)
    img = Image.new('RGB', (width, height), color=(240, 248, 255))
    draw = ImageDraw.Draw(img)
    
    # Gradient fon (yuqoridan pastga)
    for i in range(height):
        color = (240 - i//10, 248 - i//15, 255)
        draw.line([(0, i), (width, i)], fill=color)
    
    try:
        # Koreys shrifti (NanumGothic yoki boshqa koreys shrifti)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 45)
        font_header = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 32)
        font_text = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 28)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 22)
    except:
        try:
            # Alternative: DejaVu (emoji uchun)
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 45)
            font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        except:
            font_title = ImageFont.load_default()
            font_header = ImageFont.load_default()
            font_text = ImageFont.load_default()
            font_small = ImageFont.load_default()
    
    # Sarlavha fonini chizish
    draw.rounded_rectangle([(20, 20), (880, 140)], radius=15, fill=(65, 105, 225), outline=(0, 0, 139), width=3)
    
    # Sarlavha matni
    draw.text((50, 40), f"🏢 {workplace_name}", fill=(255, 255, 255), font=font_title)
    draw.text((50, 95), f"📅 {year}년 {month}월", fill=(255, 255, 255), font=font_header)
    
    # Hafta kunlari header
    draw.rounded_rectangle([(40, 170), (860, 220)], radius=10, fill=(100, 149, 237), outline=(70, 130, 180), width=2)
    
    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
    x_start = 70
    spacing = 110
    
    for i, day in enumerate(weekday_names):
        x_pos = x_start + i * spacing
        draw.text((x_pos, 180), day, fill=(255, 255, 255), font=font_header)
    
    # Kalendar kunlari (KATTAROQ KATAKCHALAR)
    days_in_month = calendar.monthrange(year, month)[1]
    first_day = datetime(year, month, 1)
    start_weekday = first_day.weekday()
    
    y_pos = 250
    x_pos = x_start + start_weekday * spacing
    
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        hours = work_dict.get(date_str, None)
        
        # Katakcha fonini chizish (KATTAROQ)
        box_x1 = x_pos - 45
        box_y1 = y_pos - 10
        box_x2 = x_pos + 65
        box_y2 = y_pos + 95  # Balandlikni oshirdik
        
        if hours is not None:
            if hours == 0:
                # Dam olish kuni - qizil
                draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=8, fill=(255, 200, 200), outline=(255, 100, 100), width=2)
            else:
                # Ish kuni - yashil
                draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=8, fill=(200, 255, 200), outline=(100, 200, 100), width=2)
        else:
            # Bo'sh kun - kulrang
            draw.rounded_rectangle([(box_x1, box_y1), (box_x2, box_y2)], radius=8, fill=(240, 240, 240), outline=(200, 200, 200), width=1)
        
        # Kun raqami
        draw.text((x_pos - 10, y_pos), str(day), fill=(0, 0, 0), font=font_text)
        
        # Soat yoki dam olish belgisi (KATTAROQ MATN)
        if hours is not None:
            if hours == 0:
                draw.text((x_pos - 25, y_pos + 40), "휴무", fill=(255, 0, 0), font=font_text)
            else:
                h_str = f"{hours}시간" if hours != int(hours) else f"{int(hours)}시간"
                text_width = draw.textlength(h_str, font=font_small)
                draw.text((x_pos - text_width//2 + 10, y_pos + 40), h_str, fill=(0, 100, 0), font=font_small)
        
        # Keyingi kun
        date_obj = datetime(year, month, day)
        if date_obj.weekday() == 6:  # Yakshanba
            y_pos += 115  # Qator orasini oshirdik
            x_pos = x_start
        else:
            x_pos += spacing
    
    # Natija qismi
    summary_y = y_pos + 120
    draw.rounded_rectangle([(40, summary_y), (860, summary_y + 220)], radius=15, fill=(255, 250, 205), outline=(255, 215, 0), width=3)
    
    # Natija matni
    draw.text((60, summary_y + 20), f"⏱️ 총 근무시간: {total_hours}시간", fill=(0, 0, 0), font=font_header)
    draw.text((60, summary_y + 65), f"💰 세전 급여: {gross:,.0f}원", fill=(0, 0, 0), font=font_text)
    draw.text((60, summary_y + 105), f"📉 세금 ({tax_rate}%): {tax:,.0f}원", fill=(139, 0, 0), font=font_text)
    
    # Oxirgi qator (katta shrift)
    draw.text((60, summary_y + 155), f"💵 실수령액: {net:,.0f}원", fill=(0, 100, 0), font=font_title)
    
    # Rasmni bytes'ga o'girish
    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    
    return bio