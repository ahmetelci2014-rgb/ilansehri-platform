"""Türkiye konum seçimleri için hafif başlangıç kataloğu.

Şehir listesi ulusal seçim sunar. İlçe ve mahalle önerileri serbest metin
alanlarını destekler; katalogda olmayan konumlar da yazılabilir.
"""

TURKEY_CITIES = (
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara",
    "Antalya", "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl",
    "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum",
    "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum",
    "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkâri", "Hatay",
    "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu",
    "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya",
    "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş",
    "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt",
    "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli",
    "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray",
    "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın",
    "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce",
)

CITY_CHOICES = tuple((city, city) for city in TURKEY_CITIES)

DISTRICTS_BY_CITY = {
    "Şanlıurfa": (
        "Akçakale", "Birecik", "Bozova", "Ceylanpınar", "Eyyübiye",
        "Halfeti", "Haliliye", "Harran", "Hilvan", "Karaköprü", "Siverek",
        "Suruç", "Viranşehir",
    ),
    "Gaziantep": (
        "Araban", "İslahiye", "Karkamış", "Nizip", "Nurdağı", "Oğuzeli",
        "Şahinbey", "Şehitkamil", "Yavuzeli",
    ),
    "Diyarbakır": (
        "Bağlar", "Bismil", "Çermik", "Çınar", "Çüngüş", "Dicle", "Eğil",
        "Ergani", "Hani", "Hazro", "Kayapınar", "Kocaköy", "Kulp", "Lice",
        "Silvan", "Sur", "Yenişehir",
    ),
    "İstanbul": (
        "Adalar", "Arnavutköy", "Ataşehir", "Avcılar", "Bağcılar", "Bahçelievler",
        "Bakırköy", "Başakşehir", "Bayrampaşa", "Beşiktaş", "Beykoz", "Beylikdüzü",
        "Beyoğlu", "Büyükçekmece", "Çatalca", "Çekmeköy", "Esenler", "Esenyurt",
        "Eyüpsultan", "Fatih", "Gaziosmanpaşa", "Güngören", "Kadıköy", "Kağıthane",
        "Kartal", "Küçükçekmece", "Maltepe", "Pendik", "Sancaktepe", "Sarıyer",
        "Silivri", "Sultanbeyli", "Sultangazi", "Şile", "Şişli", "Tuzla",
        "Ümraniye", "Üsküdar", "Zeytinburnu",
    ),
    "Ankara": (
        "Akyurt", "Altındağ", "Ayaş", "Bala", "Beypazarı", "Çamlıdere", "Çankaya",
        "Çubuk", "Elmadağ", "Etimesgut", "Evren", "Gölbaşı", "Güdül", "Haymana",
        "Kahramankazan", "Kalecik", "Keçiören", "Kızılcahamam", "Mamak", "Nallıhan",
        "Polatlı", "Pursaklar", "Sincan", "Şereflikoçhisar", "Yenimahalle",
    ),
    "İzmir": (
        "Aliağa", "Balçova", "Bayındır", "Bayraklı", "Bergama", "Beydağ", "Bornova",
        "Buca", "Çeşme", "Çiğli", "Dikili", "Foça", "Gaziemir", "Güzelbahçe",
        "Karabağlar", "Karaburun", "Karşıyaka", "Kemalpaşa", "Kınık", "Kiraz",
        "Konak", "Menderes", "Menemen", "Narlıdere", "Ödemiş", "Seferihisar",
        "Selçuk", "Tire", "Torbalı", "Urla",
    ),
    "Adana": (
        "Aladağ", "Ceyhan", "Çukurova", "Feke", "İmamoğlu", "Karaisalı", "Karataş",
        "Kozan", "Pozantı", "Saimbeyli", "Sarıçam", "Seyhan", "Tufanbeyli",
        "Yumurtalık", "Yüreğir",
    ),
    "Mersin": (
        "Akdeniz", "Anamur", "Aydıncık", "Bozyazı", "Çamlıyayla", "Erdemli",
        "Gülnar", "Mezitli", "Mut", "Silifke", "Tarsus", "Toroslar", "Yenişehir",
    ),
    "Antalya": (
        "Akseki", "Aksu", "Alanya", "Demre", "Döşemealtı", "Elmalı", "Finike",
        "Gazipaşa", "Gündoğmuş", "İbradı", "Kaş", "Kemer", "Kepez", "Konyaaltı",
        "Korkuteli", "Kumluca", "Manavgat", "Muratpaşa", "Serik",
    ),
    "Bursa": (
        "Büyükorhan", "Gemlik", "Gürsu", "Harmancık", "İnegöl", "İznik", "Karacabey",
        "Keles", "Kestel", "Mudanya", "Mustafakemalpaşa", "Nilüfer", "Orhaneli",
        "Orhangazi", "Osmangazi", "Yenişehir", "Yıldırım",
    ),
    "Konya": (
        "Ahırlı", "Akören", "Akşehir", "Altınekin", "Beyşehir", "Bozkır", "Cihanbeyli",
        "Çeltik", "Çumra", "Derbent", "Derebucak", "Doğanhisar", "Emirgazi", "Ereğli",
        "Güneysınır", "Hadim", "Halkapınar", "Hüyük", "Ilgın", "Kadınhanı", "Karapınar",
        "Karatay", "Kulu", "Meram", "Sarayönü", "Selçuklu", "Seydişehir", "Taşkent",
        "Tuzlukçu", "Yalıhüyük", "Yunak",
    ),
}

NEIGHBORHOODS_BY_DISTRICT = {
    "Şanlıurfa|Karaköprü": (
        "Akbayır", "Akpıyar", "Atakent", "Batıkent", "Doğukent", "Esentepe",
        "Karşıyaka", "Maşuk", "Narlıkuyu", "Seyrantepe",
    ),
    "Şanlıurfa|Haliliye": (
        "Bahçelievler", "Bamyasuyu", "Devteyşti", "Ertuğrul Gazi", "İpekyol",
        "Kamberiye", "Paşabağı", "Sırrın", "Şair Nabi", "Yenişehir",
    ),
    "Şanlıurfa|Eyyübiye": (
        "Akşemsettin", "Balıklıgöl", "Direkli", "Eyyüp Nebi", "Hayati Harrani",
        "Muradiye", "Onikiler", "Selçuklu", "Yenice", "Yusufpaşa",
    ),
}


def get_districts(city: str) -> tuple[str, ...]:
    return DISTRICTS_BY_CITY.get(city, ())


def get_neighborhoods(city: str, district: str) -> tuple[str, ...]:
    return NEIGHBORHOODS_BY_DISTRICT.get(f"{city}|{district}", ())



# v1.25.2 — konum yazımı ve dış adres servislerinden gelen isimleri
# İlan Şehri'nin Türkiye konum sözleşmesine uyarlama yardımcıları.
def _location_key(value: str) -> str:
    return " ".join(
        str(value or "")
        .replace("İ", "i")
        .replace("I", "ı")
        .split()
    ).casefold()


def _strip_location_suffix(value: str, suffixes: tuple[str, ...]) -> str:
    cleaned = " ".join(str(value or "").split()).strip(" ,-")
    for suffix in suffixes:
        if _location_key(cleaned).endswith(_location_key(suffix)):
            cleaned = cleaned[: -len(suffix)].strip(" ,-")
            break
    return cleaned


def canonicalize_city(value: str) -> str:
    key = _location_key(value)
    if not key:
        return ""
    for city in TURKEY_CITIES:
        if _location_key(city) == key:
            return city
    return ""


def canonicalize_district(city: str, value: str) -> str:
    cleaned = _strip_location_suffix(
        value,
        (" İlçesi", " ilçesi"),
    )
    key = _location_key(cleaned)
    if not key:
        return ""
    for district in get_districts(city):
        if _location_key(district) == key:
            return district
    return cleaned


def canonicalize_neighborhood(
    city: str,
    district: str,
    value: str,
) -> str:
    cleaned = _strip_location_suffix(
        value,
        (" Mahallesi", " mahallesi", " Mah.", " mah."),
    )
    key = _location_key(cleaned)
    if not key:
        return ""
    for neighborhood in get_neighborhoods(city, district):
        if _location_key(neighborhood) == key:
            return neighborhood
    return cleaned
