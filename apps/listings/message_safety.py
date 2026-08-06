from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


_URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>{}\[\]]+", re.IGNORECASE)
_SHORT_LINK_RE = re.compile(
    r"(?:https?://)?(?:bit\.ly|tinyurl\.com|t\.co|cutt\.ly|shorturl\.at|is\.gd|rb\.gy|rebrand\.ly)/",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MessageSafetyResult:
    level: str
    score: int
    reasons: tuple[str, ...]
    flags: tuple[str, ...]

    @property
    def is_risky(self) -> bool:
        return self.level != "safe"

    @property
    def is_high_risk(self) -> bool:
        return self.level in {"high", "critical"}

    @property
    def requires_confirmation(self) -> bool:
        return self.is_high_risk

    @property
    def label(self) -> str:
        return {
            "safe": "Belirgin risk bulunmadı",
            "medium": "Dikkat gerektiren mesaj",
            "high": "Yüksek risk uyarısı",
            "critical": "Kritik güvenlik uyarısı",
        }[self.level]

    @property
    def advice(self) -> str:
        if self.level == "critical":
            return "Şifre, doğrulama kodu, kart bilgisi veya uzaktan erişim paylaşma. İşlemi durdurup kullanıcıyı bildir."
        if self.level == "high":
            return "Ödeme yapmadan ve bağlantı açmadan önce karşı tarafı ve işlem ayrıntılarını doğrula."
        if self.level == "medium":
            return "Platform dışına çıkarken, kapora gönderirken veya bağlantı açarken dikkatli ol."
        return "Ödeme ve doğrulama bilgilerini hiçbir kullanıcıyla paylaşma."


def _normalize(value: object) -> str:
    text = str(value or "").lower().strip()
    text = text.translate(str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"}))
    text = unicodedata.normalize("NFKD", text)
    return "".join(char for char in text if not unicodedata.combining(char))


def _has_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def analyze_message(value: object) -> MessageSafetyResult:
    raw = str(value or "")
    text = _normalize(raw)
    score = 0
    reasons: list[str] = []
    flags: list[str] = []

    def add(points: int, flag: str, reason: str) -> None:
        nonlocal score
        score += points
        if flag not in flags:
            flags.append(flag)
        if reason not in reasons:
            reasons.append(reason)

    credential_phrases = (
        "dogrulama kodu", "dogrulama kodunu", "sms kodu", "sms kodunu", "onay kodu",
        "tek kullanimlik kod", "otp kodu", "kart sifresi", "internet bankaciligi sifresi",
        "e devlet sifresi", "e-devlet sifresi", "cvv kodu", "guvenlik kodunu gonder",
        "parolani gonder", "sifreni gonder",
    )
    if _has_any(text, credential_phrases):
        add(78, "credential", "Şifre veya doğrulama kodu talebi içeriyor")

    identity_phrases = (
        "tc kimlik", "kimlik fotograf", "kart fotograf", "banka kartinin fotograf",
        "kredi kartinin fotograf", "ruhsatin fotografini gonder", "selfie ile kimlik",
    )
    if _has_any(text, identity_phrases):
        add(52, "identity", "Kimlik veya kart görüntüsü paylaşımı istiyor")

    remote_access_phrases = (
        "anydesk", "teamviewer", "uzak masaustu", "uzaktan baglan", "ekran paylas",
        "telefonuna baglan", "bilgisayarina baglan",
    )
    if _has_any(text, remote_access_phrases):
        add(68, "remote_access", "Cihaza uzaktan erişim veya ekran paylaşımı istiyor")

    payment_phrases = (
        "kapora", "on odeme", "havale yap", "eft yap", "ibana gonder", "iban'a gonder",
        "odeme linki", "parayi gonder", "ucreti yatir", "hesaba yatir", "kurye parasi",
    )
    if _has_any(text, payment_phrases):
        add(24, "advance_payment", "Ön ödeme, havale veya kapora ifadesi içeriyor")

    urgency_phrases = (
        "hemen gonder", "simdi gonder", "bugun yatir", "acele et", "son sans",
        "beklemeden odeme", "hemen odeme", "yalnizca bugun",
    )
    if _has_any(text, urgency_phrases):
        add(18, "urgency", "Acele ödeme veya baskı ifadesi içeriyor")

    off_platform_phrases = (
        "whatsapp'tan", "whatsapptan", "whatsapp a gec", "whatsappa gec", "telegramdan",
        "telegram'a gec", "instagramdan yaz", "platform disinda", "buradan yazma",
    )
    if _has_any(text, off_platform_phrases):
        add(14, "off_platform", "Görüşmeyi platform dışına taşıma isteği içeriyor")

    alternative_payment_phrases = (
        "kripto ile ode", "usdt gonder", "bitcoin gonder", "hediye karti al",
        "gift card", "steam kart", "google play kart",
    )
    if _has_any(text, alternative_payment_phrases):
        add(42, "alternative_payment", "Takibi zor bir ödeme yöntemi öneriyor")

    urls = _URL_RE.findall(raw)
    if urls:
        if any(_SHORT_LINK_RE.search(url) for url in urls):
            add(48, "short_link", "Kısaltılmış ve hedefi görünmeyen bağlantı içeriyor")
        else:
            add(16, "external_link", "Harici internet bağlantısı içeriyor")

    score = min(100, score)
    if score >= 70:
        level = "critical"
    elif score >= 45:
        level = "high"
    elif score >= 20:
        level = "medium"
    else:
        level = "safe"

    return MessageSafetyResult(
        level=level,
        score=score,
        reasons=tuple(reasons[:4]),
        flags=tuple(flags),
    )


def safe_notification_preview(sender_name: str, body: str) -> str:
    result = analyze_message(body)
    if result.is_high_risk:
        return f"{sender_name}: Güvenlik uyarısı içeren yeni bir mesaj gönderdi."
    return f"{sender_name}: {body[:100]}"
