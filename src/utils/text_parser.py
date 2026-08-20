"""
Erkin matndan (masalan "9 soat lekin oldindan pul oldim") soat sonini
va qolgan matnni (eslatma) ajratib olish uchun yordamchi funksiya.
"""
import re


def parse_hours_and_note(text: str):
    """Matndan birinchi topilgan sonni soat sifatida, qolgan matnni esa
    eslatma sifatida ajratib qaytaradi.

    Misollar:
        "9"                                  -> (9.0, None)
        "9.5"                                -> (9.5, None)
        "9,5"                                -> (9.5, None)
        "9 soat lekin oldindan pul oldim"    -> (9.0, "9 soat lekin oldindan pul oldim")

    Agar matnda umuman son topilmasa -> (None, None) qaytaradi.
    """
    if not text:
        return None, None

    text = text.strip()
    match = re.search(r'\d+([.,]\d+)?', text)
    if not match:
        return None, None

    num_str = match.group(0).replace(',', '.')
    try:
        hours = float(num_str)
    except ValueError:
        return None, None

    # Agar matn faqat shu sondan (bo'sh joylar bilan) iborat bo'lsa - eslatma yo'q
    remainder = (text[:match.start()] + text[match.end():]).strip()
    note = text if remainder else None

    return hours, note