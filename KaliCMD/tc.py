import textwrap

print("\n📘 Linux Terminal komandalarining to‘liq lug‘ati yuklanmoqda...\n")

ltc = {
    "chapter-1": {
        "pwd": "Joriy ishchi katalogni (working directory) ko‘rsatadi.",
        "whoami": "Hozirda tizimda ishlayotgan foydalanuvchi nomini ko‘rsatadi.",
        "cd": "Katalogga kirish yoki orqaga qaytish uchun ishlatiladi. (ex: cd /home/user yoki cd ..)",
        "ls": "Katalog ichidagi fayllarni ko‘rsatadi.",
        "ls -la": "Fayl va kataloglarni to‘liq ma’lumot bilan (hajmi, ruxsatlar, vaqt) ko‘rsatadi.",
        "man": "Terminaldagi biror bir buyruq haqida to‘liq ma’lumot beruvchi code. ",
        "locate": "Berilgan so‘z bo‘yicha faylni qidiradi (faqat 24 soat ichida yangilangan indeksdan).",
        "whereis": "Binary, matn sahifalari va konfiguratsiya fayllarini topadi.",
        "which": "PATH o‘zgaruvchisi ichidan dastur joylashgan joyni topadi.",
        "find": "Fayl yoki katalogni chuqur qidirish uchun eng qudratli buyruq ",
        "grep": "Berilgan so‘zni yoki naqshni matndan qidiradi. ",
        "ps": "Ayni vaqtda tizimda ishlayotgan jarayonlarni (process) ko‘rsatadi.",
        "echo": "Terminalga matn yoki o‘zgaruvchini chiqaradi. Faylga yozishda ham ishlatiladi.",
        "cat": "Fayl ichidagi matnni o'qiydi yo'q bo'lsa yaratadi",
        "cat > ": "Faylga yozadi (mavjud faylni tozalaydi). Saqlash uchun Ctrl+D bosing.",
        "cat >> ": "Faylga yangi satrlar qo‘shadi (mavjud ma’lumot o‘chmaydi).",
        "touch": "Bo‘sh fayl yaratadi yoki mavjud faylning so‘nggi o‘zgartirish vaqtini yangilaydi.",
        "nano": "Terminalda matn muharriri (Ctrl+O saqlash, Ctrl+X chiqish).",
        "cp": "Fayl nusxasini ko‘chirish ",
        "cp -r": "Katalogni ichidagi fayllari bilan birga ko‘chirish.",
        "mv": "Fayl yoki katalogni ko‘chirish yoki nomini o‘zgartirish.",
        "rm": "Faylni o‘chirish (ehtiyot bo‘lish kerak!).",
        "rm -r": "Katalogni barcha ichki fayllari bilan o‘chirish ⚠️ juda xavfli!",
        "echo 'text' | sudo tee file": "Root huquqida faylga yozish uchun ishlatiladi.(! tee bilan)",
        "sudo bash -c 'echo text > file'": "Root faylga yozishning boshqa usuli. (! bash bilan)",
        "tee -a file": "Faylga yozish (append rejimida).",
        "cp file file.bak": "O‘zgartirishdan oldin backup yaratish uchun."
    },

    "chapter-2": {
        "head": "Faylning birinchi satrlarini ko‘rsatadi. (ex: **** -10 file.txt)",
        "tail": "Faylning oxirgi satrlarini ko‘rsatadi. (ex: **** -20 file.txt)",
        "nl": "Har bir qatorga raqam beradi (bo‘sh qatorlar raqamlanmaydi!!!).",
        "nl -ba": "Har bir qatorga, shu jumladan bo‘sh qatorlarga ham raqam beradi.",
        "sed": "Matnni avtomatik tahrirlash uchun ishlatiladi. Unda qidirish, almashtirish, o‘chirish\
            kabi amallar bajariladi. (ex: `*** 's/old/new/g' file.txt` — 'old' so‘zini 'new' ga almashtiradi)",        
        "sed -i": "Faylni joyida (bevosita) o‘zgartiradi. Yangi fayl yaratmaydi — o‘zini o‘zi yangilaydi. \
            (ex: `*** -i 's/localhost/127.0.0.1/g' config.txt` — config.txt ichidagi 'localhost' ni IP ga almashtiradi)",
        "sed -a": "Har bir mos kelgan qator ostiga yangi qator qo‘shib beradi (append). \
            (ex: `*** '/error/a\YANGI QATOR' log.txt` — log.txt dagi har bir 'error' so‘zidan keyin 'YANGI QATOR' qo‘shadi)",
        "more": "Uzun fayllarni bosqichma-bosqich ko‘rsatadi ya'ni faylni o'qish uchun. Pastga tushish uchun 'space', chiqish uchun 'q'.",
        "less": "Faylni erkin ko‘rish uchun qulay vosita — / bilan qidirish, n bilan davom ettirish mumkin. 'q' bilan chiqiladi."

    },

    "chapter-3": {
        "ifconfig": "Tarmoq interfeyslarini (IP, MAC va boshqalar) ko‘rsatadi.",
        "ip addr show": "ifconfig ning zamonaviy ekvivalenti, ko‘proq ma’lumot beradi.",
        "iwconfig": "Simsiz tarmoq (Wi-Fi) interfeysi haqidagi ma’lumotlar.",
        "ifconfig eth0 or wlan0 192.168.1.5": "Statik IP manzilni qo‘lda o‘rnatish.",
        "ifconfig eth0 netmask 255.255.255.0 broadcast 192.168.1.255": "Subnet va broadcast manzilini sozlash.",
        "ifconfig eth0 or wlan0 hw ether 00:11:22:33:44:AA": "MAC manzilni o‘zgartirish.",
        "ifconfig eth0 or wlan0 down/up": "Tarmoq interfeysini o‘chirish yoki yoqish.",
        "DHCP": "Qurilmalarga IP va boshqa tarmoq sozlamalarini avtomatik beradi.",
        "dhclient eth0 or wlan0 ": "DHCP orqali yangi IP olish.",
        "dhclient -r eth0 or wlan0": "Avval olingan IP manzilni bo‘shatish.kill qilish",
        "dhclient -v eth0 or wlan0 ": "DHCP jarayonini to‘liq ko‘rsatadi (verbose rejimi).",
        "dig example.com": "Saytning IP manzilini ko‘rsatadi.",
        "dig example.com ns": "Saytning DNS (Name Server) yozuvlarini ko‘rsatadi.",
        "dig example.com mx": "Saytning email server (MX) yozuvlarini ko‘rsatadi.",
        "dnsspoof": "DNS so‘rovlarini soxtalashtirish uchun (xavfsizlik testlarida ishlatiladi).",
        "ettercap": "ARP spoofing, sniffing va MITM hujumlari uchun kuchli vosita."
    },

    "chapter-4": {
        "apt-cache search package": "Paket tizimda mavjudmi yoki yo‘qmi, qidiradi.",
        "apt-get install package": "Yangi dastur o‘rnatadi.",
        "apt-get remove package": "Dastur o‘chiradi (lekin konfiguratsiya fayllarini qoldiradi).",
        "apt-get purge package": "Dastur bilan birga konfiguratsiya fayllarini ham o‘chiradi.",
        "apt-get autoremove": "Keraksiz bog‘liq kutubxonalarni o‘chiradi.",
        "apt update": "Paket ro‘yxatini yangilaydi (lekin o‘rnatmaydi).",
        "apt-get upgrade": "Mavjud barcha paketlarni yangilaydi.",
        "sources.list": "Repository (dasturiy manbalar) ro‘yxatini saqlaydigan fayl.",
        "synaptic": "Paketlarni boshqarish uchun grafik interfeys."
    },
}

def print_chapters():
    """Har bir bobdagi komandalarni tartibli chiqaradigan"""
    for chapter, commands in ltc.items():
        indent = " " * 15
        print(f"\n{indent}{'=' * 35}")
        print(f"{indent}📘 {chapter.upper()} komandalar ro‘yxati")
        print(f"{indent}{'=' * 35}\n")
        for cmd, desc in commands.items():
            wrapped = textwrap.fill(desc.strip(), width=60, subsequent_indent=" " * 8)
            print(f"  {cmd:<30} ➤ {wrapped}\n{'_' * 70}")

if __name__ == "__main__":
    print_chapters()
