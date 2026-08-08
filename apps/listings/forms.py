from __future__ import annotations

from datetime import timedelta
import re

from django import forms
from django.utils import timezone

from .catalog import (
    category_detail_fields,
    category_detail_profile,
    category_market_kind,
    category_matches_kind,
    category_path,
    category_required_fields,
)
from .locations import (
    CITY_CHOICES,
    canonicalize_district,
    canonicalize_neighborhood,
)
from .message_safety import analyze_message
from .models import (
    Appointment,
    Category,
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




class CategorySelect(forms.Select):
    """Kategori seçeneklerine ilan türü ve yaprak bilgisi ekler."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        instance = getattr(value, "instance", None)
        if instance is not None:
            option["attrs"]["data-category-kind"] = category_market_kind(instance)
            children = getattr(instance, "_prefetched_objects_cache", {}).get("children")
            has_children = any(item.is_active for item in children) if children is not None else instance.children.filter(is_active=True).exists()
            option["attrs"]["data-category-leaf"] = "0" if has_children else "1"
            option["attrs"]["data-category-path"] = category_path(instance)
            option["attrs"]["data-category-slug"] = instance.slug
            option["attrs"]["data-category-profile"] = category_detail_profile(instance)
            option["attrs"]["data-category-fields"] = ",".join(category_detail_fields(instance))
        return option


class CategoryChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        prefix = "— " if obj.parent_id else ""
        children = getattr(obj, "_prefetched_objects_cache", {}).get("children")
        has_children = any(item.is_active for item in children) if children is not None else obj.children.filter(is_active=True).exists()
        suffix = " (tümü)" if has_children else ""
        return f"{prefix}{category_path(obj)}{suffix}"


class ListingForm(forms.ModelForm):
    category = CategoryChoiceField(
        queryset=Category.objects.none(),
        label="Kategori",
        empty_label="Önce ilan türünü, sonra alt kategoriyi seçin",
        widget=CategorySelect(attrs={"data-category-select": "true"}),
    )
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
        self.fields["category"].queryset = (
            Category.objects.filter(is_active=True)
            .select_related("parent", "parent__parent")
            .prefetch_related("children")
            .order_by("parent__sort_order", "parent__name", "sort_order", "name")
        )
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

        category = cleaned.get("category")
        city = (cleaned.get("city") or "").strip()
        district = canonicalize_district(
            city,
            cleaned.get("district") or "",
        )
        neighborhood = canonicalize_neighborhood(
            city,
            district,
            cleaned.get("neighborhood") or "",
        )
        cleaned["city"] = city
        cleaned["district"] = district
        cleaned["neighborhood"] = neighborhood

        if category:
            if not category_matches_kind(category, kind):
                self.add_error("category", "Seçilen kategori ilan türüyle uyuşmuyor.")
            if category.children.filter(is_active=True).exists():
                self.add_error("category", "Daha doğru sonuçlar için bir alt kategori seç.")

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

        detail_required_messages = {
            "condition": "Ürün / parça durumunu belirt.",
            "brand": "Markayı belirt.",
            "model_name": "Modeli belirt.",
            "model_year": "Model yılını belirt.",
            "room_count": "Oda sayısını belirt.",
            "area_m2": "Metrekare bilgisini belirt.",
            "service_area": "Hizmet bölgesini belirt.",
            "fee_type": "Ücret tipini seç.",
            "job_type": "Çalışma şeklini seç.",
        }

        for field_name in category_required_fields(
            category,
            kind,
            action,
        ):
            if not cleaned.get(field_name):
                self.add_error(
                    field_name,
                    detail_required_messages[field_name],
                )

        year = cleaned.get("model_year")
        if year and not 1900 <= year <= timezone.now().year + 1:
            self.add_error(
                "model_year",
                "Geçerli bir model yılı gir.",
            )

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


class AppointmentForm(forms.ModelForm):
    DURATION_CHOICES = (
        (15, "15 dakika"),
        (30, "30 dakika"),
        (45, "45 dakika"),
        (60, "1 saat"),
        (90, "1,5 saat"),
        (120, "2 saat"),
    )

    duration_minutes = forms.TypedChoiceField(
        label="Tahmini süre",
        choices=DURATION_CHOICES,
        coerce=int,
        empty_value=30,
    )

    class Meta:
        model = Appointment
        fields = (
            "appointment_type",
            "starts_at",
            "duration_minutes",
            "city",
            "district",
            "place",
            "note",
        )
        labels = {
            "appointment_type": "Görüşme türü",
            "starts_at": "Tarih ve saat",
            "city": "Şehir",
            "district": "İlçe",
            "place": "Buluşma noktası / görüşme bilgisi",
            "note": "Kısa not",
        }
        widgets = {
            "starts_at": forms.DateTimeInput(
                attrs={"type": "datetime-local", "step": "900"},
                format="%Y-%m-%dT%H:%M",
            ),
            "city": forms.TextInput(attrs={"autocomplete": "address-level1", "placeholder": "Şehir"}),
            "district": forms.TextInput(attrs={"autocomplete": "address-level2", "placeholder": "İlçe"}),
            "place": forms.TextInput(
                attrs={
                    "placeholder": "Örn. AVM danışma önü veya görüşme kanalı",
                    "maxlength": "180",
                }
            ),
            "note": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Ürün kontrolü, teslim veya görüşme için gerekli kısa bilgiyi yaz...",
                    "maxlength": "500",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["starts_at"].input_formats = ("%Y-%m-%dT%H:%M",)

    def clean_starts_at(self):
        starts_at = self.cleaned_data["starts_at"]
        now = timezone.now()
        if starts_at < now + timedelta(minutes=30):
            raise forms.ValidationError("Randevu en az 30 dakika sonrası için oluşturulmalıdır.")
        if starts_at > now + timedelta(days=90):
            raise forms.ValidationError("Randevu en fazla 90 gün sonrası için oluşturulabilir.")
        return starts_at

    def clean(self):
        cleaned = super().clean()
        appointment_type = cleaned.get("appointment_type")
        city = (cleaned.get("city") or "").strip()
        district = (cleaned.get("district") or "").strip()
        place = (cleaned.get("place") or "").strip()
        note = (cleaned.get("note") or "").strip()

        if appointment_type in {Appointment.Type.IN_PERSON, Appointment.Type.DELIVERY}:
            if not city:
                self.add_error("city", "Yüz yüze görüşme için şehri yaz.")
            if not district:
                self.add_error("district", "Yüz yüze görüşme için ilçeyi yaz.")
            if len(place) < 5:
                self.add_error("place", "Güvenli ve anlaşılır bir buluşma noktası yaz.")
        elif not place:
            cleaned["place"] = "Platform içinden ayrıntı paylaşılacak"

        private_patterns = re.compile(
            r"(?:https?://|www\.|(?:\+?90|0)?5\d{9}|[\w.+-]+@[\w-]+(?:\.[\w-]+)+)",
            re.IGNORECASE,
        )
        if private_patterns.search(place):
            self.add_error(
                "place",
                "Görüşme bilgisinde bağlantı, telefon numarası veya e-posta paylaşma; ayrıntıyı platform mesajında konuş.",
            )
        if private_patterns.search(note):
            self.add_error("note", "Not alanında bağlantı, telefon numarası veya e-posta paylaşma.")
        cleaned["city"] = city
        cleaned["district"] = district
        cleaned["place"] = place or cleaned.get("place", "")
        cleaned["note"] = note
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
            "comment": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "İletişim, doğruluk ve teslim deneyimini anlat...",
                    "maxlength": "1000",
                }
            ),
        }

    def clean(self):
        cleaned = super().clean()
        rating = cleaned.get("rating")
        comment = (cleaned.get("comment") or "").strip()
        if rating and rating <= 2 and len(comment) < 20:
            self.add_error("comment", "1 veya 2 yıldızlı değerlendirmede en az 20 karakter açıklama yaz.")
        if re.search(
            r"(?:https?://|www\.|(?:\+?90|0)?5\d{9}|[\w.+-]+@[\w-]+(?:\.[\w-]+)+)",
            comment,
            re.IGNORECASE,
        ):
            self.add_error("comment", "Değerlendirmede bağlantı, telefon numarası veya e-posta paylaşma.")
        cleaned["comment"] = comment
        return cleaned


class HandoverCodeForm(forms.Form):
    code = forms.CharField(
        label="6 haneli teslim kodu",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "pattern": "[0-9]{6}",
                "placeholder": "000000",
            }
        ),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not code.isdigit() or len(code) != 6:
            raise forms.ValidationError("Teslim kodu 6 rakamdan oluşmalıdır.")
        return code


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
