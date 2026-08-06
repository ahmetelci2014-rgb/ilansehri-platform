from __future__ import annotations

from django import forms
from django.utils import timezone

from .locations import CITY_CHOICES
from .message_safety import analyze_message
from .models import (
    Listing,
    ListingReport,
    Message,
    Offer,
    Review,
    SavedSearch,
    Transaction,
)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget",
            MultipleFileInput(
                attrs={
                    "accept": ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp",
                    "data-image-input": "true",
                    "class": "file-input",
                }
            ),
        )
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data]
        return [single_file_clean(data, initial)] if data else []


class ListingForm(forms.ModelForm):
    search_tags_text = forms.CharField(
        required=False,
        label="Arama etiketleri",
        help_text="Virgülle ayır. En fazla 20 kısa etiket.",
        widget=forms.TextInput(attrs={"placeholder": "Örn. bluetooth, kablosuz, siyah"}),
    )
    technical_features_text = forms.CharField(
        required=False,
        label="Ek teknik özellikler",
        help_text="Her satıra bir özellik yaz. Yapay zekâ önerilerini kontrol ederek düzenleyebilirsin.",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Örn. 128 GB depolama\nKablosuz bağlantı\nKutusu mevcut"}),
    )
    images = MultipleFileField(
        required=False,
        label="İlan fotoğrafları",
        help_text="Toplam en fazla 10 fotoğraf. İlk yeni fotoğraf, kapak yoksa kapak olur.",
    )
    city = forms.ChoiceField(
        choices=(("", "Şehir seçin"), *CITY_CHOICES),
        label="Şehir",
        widget=forms.Select(attrs={"data-location-city": "true"}),
    )
    district = forms.CharField(
        label="İlçe",
        widget=forms.TextInput(
            attrs={
                "placeholder": "İlçe seçin veya yazın",
                "list": "district-options",
                "data-location-district": "true",
                "autocomplete": "address-level2",
            }
        ),
    )
    latitude = forms.DecimalField(
        required=False,
        max_digits=9,
        decimal_places=6,
        widget=forms.HiddenInput(attrs={"data-listing-latitude": "true"}),
    )
    longitude = forms.DecimalField(
        required=False,
        max_digits=9,
        decimal_places=6,
        widget=forms.HiddenInput(attrs={"data-listing-longitude": "true"}),
    )
    neighborhood = forms.CharField(
        required=False,
        label="Mahalle",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Mahalle seçin veya yazın",
                "list": "neighborhood-options",
                "data-location-neighborhood": "true",
                "autocomplete": "address-level3",
            }
        ),
    )

    class Meta:
        model = Listing
        fields = [
            "kind",
            "action",
            "management_mode",
            "category",
            "title",
            "description",
            "price",
            "price_on_request",
            "is_negotiable",
            "delivery_type",
            "condition",
            "color",
            "brand",
            "model_name",
            "model_year",
            "mileage",
            "fuel_type",
            "transmission",
            "room_count",
            "area_m2",
            "building_age",
            "floor_location",
            "heating_type",
            "service_area",
            "fee_type",
            "job_type",
            "experience_level",
            "city",
            "district",
            "neighborhood",
            "latitude",
            "longitude",
        ]
        labels = {
            "kind": "İlan türü",
            "action": "Ne yapmak istiyorsun?",
            "management_mode": "İlanı kim yönetecek?",
            "condition": "Ürün / araç durumu",
            "color": "Renk",
            "price_on_request": "Fiyat yerine teklif almak istiyorum",
            "is_negotiable": "Pazarlık payı var",
            "delivery_type": "Teslim / hizmet şekli",
            "category": "Kategori",
            "price": "Fiyat",
            "brand": "Marka",
            "model_name": "Model",
            "model_year": "Model yılı",
            "mileage": "Kilometre",
            "fuel_type": "Yakıt türü",
            "transmission": "Vites",
            "room_count": "Oda sayısı",
            "area_m2": "Brüt metrekare",
            "building_age": "Bina yaşı",
            "floor_location": "Bulunduğu kat",
            "heating_type": "Isıtma türü",
            "service_area": "Hizmet bölgesi",
            "fee_type": "Ücret tipi",
            "job_type": "Çalışma şekli",
            "experience_level": "Deneyim seviyesi",
        }
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "rows": 7,
                    "placeholder": "Tüm önemli ayrıntıları, teslim koşullarını ve kullanım durumunu açıkça yaz...",
                }
            ),
            "title": forms.TextInput(attrs={"placeholder": "Kısa, anlaşılır ve açıklayıcı başlık"}),
            "price": forms.NumberInput(attrs={"min": "0", "step": "0.01", "placeholder": "0,00"}),
            "condition": forms.TextInput(attrs={"placeholder": "Örn. Sıfır, az kullanılmış, hasarsız"}),
            "color": forms.TextInput(attrs={"placeholder": "Örn. Siyah, lacivert, ahşap"}),
            "brand": forms.TextInput(attrs={"placeholder": "Örn. Toyota, Apple"}),
            "model_name": forms.TextInput(attrs={"placeholder": "Örn. Corolla, iPhone 15"}),
            "model_year": forms.NumberInput(attrs={"min": "1900", "max": "2100"}),
            "mileage": forms.NumberInput(attrs={"min": "0", "step": "1"}),
            "room_count": forms.TextInput(attrs={"placeholder": "Örn. 3+1"}),
            "area_m2": forms.NumberInput(attrs={"min": "1", "step": "1"}),
            "building_age": forms.NumberInput(attrs={"min": "0", "step": "1"}),
            "floor_location": forms.TextInput(attrs={"placeholder": "Örn. 4. kat"}),
            "heating_type": forms.TextInput(attrs={"placeholder": "Örn. Doğalgaz kombi"}),
            "service_area": forms.TextInput(attrs={"placeholder": "Örn. Karaköprü ve Haliliye"}),
            "experience_level": forms.TextInput(attrs={"placeholder": "Örn. En az 2 yıl"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_city = getattr(self.instance, "city", "")
        if current_city and current_city not in dict(self.fields["city"].choices):
            self.fields["city"].choices = (*self.fields["city"].choices, (current_city, current_city))
        self.fields["category"].queryset = self.fields["category"].queryset.filter(is_active=True)
        if not self.is_bound and getattr(self.instance, "pk", None):
            self.fields["search_tags_text"].initial = ", ".join(self.instance.search_tags or [])
            self.fields["technical_features_text"].initial = "\n".join(self.instance.technical_features or [])

    @staticmethod
    def _clean_text_list(value, *, max_items: int, max_length: int):
        if not value:
            return []
        normalized = str(value).replace(";", ",").replace("\r", "\n")
        raw_items = []
        for line in normalized.split("\n"):
            raw_items.extend(line.split(","))
        result = []
        for item in raw_items:
            cleaned = " ".join(item.strip().split())[:max_length]
            if cleaned and cleaned.casefold() not in {existing.casefold() for existing in result}:
                result.append(cleaned)
            if len(result) >= max_items:
                break
        return result

    def clean_search_tags_text(self):
        return self._clean_text_list(
            self.cleaned_data.get("search_tags_text", ""),
            max_items=20,
            max_length=40,
        )

    def clean_technical_features_text(self):
        return self._clean_text_list(
            self.cleaned_data.get("technical_features_text", ""),
            max_items=30,
            max_length=160,
        )

    def clean_images(self):
        images = self.cleaned_data.get("images", [])
        existing_count = self.instance.images.count() if self.instance.pk else 0
        if existing_count + len(images) > 10:
            raise forms.ValidationError("Bir ilana toplam en fazla 10 fotoğraf yüklenebilir.")
        for image in images:
            if image.size > 8 * 1024 * 1024:
                raise forms.ValidationError("Her fotoğraf en fazla 8 MB olabilir.")
            if not getattr(image, "content_type", "").startswith("image/"):
                raise forms.ValidationError("Yalnızca görsel dosyaları yüklenebilir.")
        return images

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        action = cleaned.get("action")
        latitude = cleaned.get("latitude")
        longitude = cleaned.get("longitude")

        if (latitude is None) != (longitude is None):
            self.add_error("latitude", "Konum koordinatları birlikte gönderilmelidir.")
            self.add_error("longitude", "Konum koordinatları birlikte gönderilmelidir.")
        if latitude is not None and not (-90 <= latitude <= 90):
            self.add_error("latitude", "Geçerli bir enlem değeri gönderilmedi.")
        if longitude is not None and not (-180 <= longitude <= 180):
            self.add_error("longitude", "Geçerli bir boylam değeri gönderilmedi.")

        allowed_actions = {
            Listing.Kind.PRODUCT: {Listing.Action.SELL, Listing.Action.RENT, Listing.Action.SWAP, Listing.Action.WANTED},
            Listing.Kind.VEHICLE: {Listing.Action.SELL, Listing.Action.RENT, Listing.Action.SWAP, Listing.Action.WANTED},
            Listing.Kind.REAL_ESTATE: {Listing.Action.SELL, Listing.Action.RENT, Listing.Action.WANTED},
            Listing.Kind.SERVICE: {Listing.Action.SERVICE_OFFER, Listing.Action.SERVICE_REQUEST},
            Listing.Kind.NEED: {Listing.Action.WANTED, Listing.Action.SERVICE_REQUEST},
            Listing.Kind.JOB: {Listing.Action.JOB_OFFER, Listing.Action.JOB_REQUEST},
        }
        if kind and action and action not in allowed_actions.get(kind, set()):
            self.add_error("action", "Seçilen ilan türü için uygun bir işlem seç.")

        price_optional_actions = {
            Listing.Action.WANTED,
            Listing.Action.SERVICE_REQUEST,
            Listing.Action.JOB_REQUEST,
        }
        if action not in price_optional_actions and not cleaned.get("price_on_request") and cleaned.get("price") is None:
            self.add_error("price", "Fiyat gir veya teklif almak istediğini işaretle.")

        if kind == Listing.Kind.PRODUCT and not cleaned.get("condition"):
            self.add_error("condition", "Ürünün durumunu belirt.")
        elif kind == Listing.Kind.VEHICLE:
            for field, message in (
                ("brand", "Araç markasını belirt."),
                ("model_name", "Araç modelini belirt."),
                ("model_year", "Model yılını belirt."),
            ):
                if not cleaned.get(field):
                    self.add_error(field, message)
            year = cleaned.get("model_year")
            if year and not 1900 <= year <= timezone.now().year + 1:
                self.add_error("model_year", "Geçerli bir model yılı gir.")
        elif kind == Listing.Kind.REAL_ESTATE:
            if not cleaned.get("room_count"):
                self.add_error("room_count", "Oda sayısını belirt.")
            if not cleaned.get("area_m2"):
                self.add_error("area_m2", "Metrekare bilgisini belirt.")
        elif kind == Listing.Kind.SERVICE:
            if not cleaned.get("service_area"):
                self.add_error("service_area", "Hizmet verdiğin bölgeyi belirt.")
            if not cleaned.get("fee_type"):
                self.add_error("fee_type", "Ücret tipini seç.")
        elif kind == Listing.Kind.JOB and not cleaned.get("job_type"):
            self.add_error("job_type", "Çalışma şeklini seç.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.search_tags = self.cleaned_data.get("search_tags_text", [])
        instance.technical_features = self.cleaned_data.get("technical_features_text", [])
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = ("amount", "message")
        labels = {"amount": "Teklif tutarı", "message": "Teklif notun"}
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4, "placeholder": "Teklif koşullarını ve teslim planını yaz..."}),
            "amount": forms.NumberInput(attrs={"min": "0", "step": "0.01", "placeholder": "TL"}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Teklif tutarı sıfırdan büyük olmalıdır.")
        return amount

    def clean_message(self):
        message = self.cleaned_data["message"].strip()
        if len(message) < 5:
            raise forms.ValidationError("Teklif notu en az 5 karakter olmalıdır.")
        return message


class CounterOfferForm(forms.Form):
    amount = forms.DecimalField(
        label="Yeni teklif tutarı",
        max_digits=14,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={"min": "0.01", "step": "0.01", "placeholder": "TL"}),
    )
    message = forms.CharField(
        label="Karşı teklif notu",
        max_length=1200,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Yeni tutarı ve teslim koşulunu kısaca açıkla...",
            }
        ),
    )

    def clean_message(self):
        message = self.cleaned_data["message"].strip()
        if len(message) < 5:
            raise forms.ValidationError("Karşı teklif notu en az 5 karakter olmalıdır.")
        return message


class MessageForm(forms.ModelForm):
    safety_confirmed = forms.BooleanField(
        required=False,
        label="Uyarıyı okudum; şifre, doğrulama kodu veya kart bilgisi paylaşmadığımı onaylıyorum.",
        widget=forms.CheckboxInput(attrs={"data-safety-confirm-checkbox": "true"}),
    )

    class Meta:
        model = Message
        fields = ("body", "attachment")
        labels = {"body": "Mesajın", "attachment": "Görsel ekle (isteğe bağlı)"}
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "İlan hakkında merak ettiğini yaz...",
                    "maxlength": "1600",
                    "data-message-safety-input": "true",
                }
            ),
            "attachment": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if len(body) < 2:
            raise forms.ValidationError("Mesaj en az 2 karakter olmalıdır.")
        return body

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")
        if attachment and attachment.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Mesaj görseli en fazla 5 MB olabilir.")
        if attachment and not getattr(attachment, "content_type", "").startswith("image/"):
            raise forms.ValidationError("Mesaja yalnızca görsel dosyası eklenebilir.")
        return attachment

    def clean(self):
        cleaned = super().clean()
        body = cleaned.get("body") or ""
        self.safety_result = analyze_message(body)
        if self.safety_result.requires_confirmation and not cleaned.get("safety_confirmed"):
            self.add_error(
                "safety_confirmed",
                "Bu mesaj yüksek riskli ifade içeriyor. Güvenlik uyarısını okuyup onay kutusunu işaretle.",
            )
        return cleaned


class ListingReportForm(forms.ModelForm):
    class Meta:
        model = ListingReport
        fields = ("reason", "details")
        labels = {"reason": "Şikâyet nedeni", "details": "Açıklama"}
        widgets = {
            "details": forms.Textarea(
                attrs={"rows": 4, "placeholder": "İnceleme ekibimizin bilmesi gereken ayrıntıları yaz..."}
            )
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "comment")
        labels = {"rating": "Puanın", "comment": "Deneyimini paylaş"}
        widgets = {
            "rating": forms.RadioSelect(choices=[(value, f"{value} yıldız") for value in range(5, 0, -1)]),
            "comment": forms.Textarea(attrs={"rows": 5, "placeholder": "İletişim, doğruluk ve teslim deneyimini anlat..."}),
        }


class TransactionDisputeForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ("dispute_reason",)
        labels = {"dispute_reason": "Uyuşmazlık nedeni"}
        widgets = {
            "dispute_reason": forms.Textarea(attrs={"rows": 6, "placeholder": "Sorunu ve çözüm beklentini ayrıntılı yaz..."})
        }

    def clean_dispute_reason(self):
        reason = self.cleaned_data["dispute_reason"].strip()
        if len(reason) < 20:
            raise forms.ValidationError("Uyuşmazlık açıklaması en az 20 karakter olmalıdır.")
        return reason


class SavedSearchForm(forms.ModelForm):
    class Meta:
        model = SavedSearch
        fields = ("name", "alert_frequency")
        labels = {"name": "Arama adı", "alert_frequency": "Bildirim sıklığı"}
        widgets = {"alert_frequency": forms.Select(attrs={"class": "saved-search-frequency"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and not self.instance.alert_enabled:
            self.initial["alert_frequency"] = SavedSearch.AlertFrequency.OFF

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Arama adı en az 2 karakter olmalıdır.")
        return name[:120]
