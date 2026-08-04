from django import forms
from django.utils import timezone

from .locations import CITY_CHOICES
from .models import Listing, ListingReport, Message, Offer


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget",
            MultipleFileInput(
                attrs={
                    "accept": "image/*",
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
    images = MultipleFileField(
        required=False,
        label="İlan fotoğrafları",
        help_text="En fazla 10 fotoğraf yükleyebilirsin. İlk fotoğraf kapak olur.",
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
            "condition",
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
        ]
        labels = {
            "kind": "İlan türü",
            "action": "Ne yapmak istiyorsun?",
            "management_mode": "İlanı kim yönetecek?",
            "condition": "Ürün / araç durumu",
            "price_on_request": "Fiyat yerine teklif almak istiyorum",
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
            "title": forms.TextInput(
                attrs={"placeholder": "Örn. 2022 model düşük kilometre otomobil"}
            ),
            "price": forms.NumberInput(
                attrs={"min": "0", "step": "0.01", "placeholder": "0,00"}
            ),
            "condition": forms.TextInput(
                attrs={"placeholder": "Örn. Sıfır, az kullanılmış, hasarsız"}
            ),
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
        self.fields["category"].queryset = self.fields["category"].queryset.filter(
            is_active=True
        )

    def clean_images(self):
        images = self.cleaned_data.get("images", [])
        if len(images) > 10:
            raise forms.ValidationError("Bir ilana en fazla 10 fotoğraf yüklenebilir.")
        for image in images:
            if image.size > 8 * 1024 * 1024:
                raise forms.ValidationError("Her fotoğraf en fazla 8 MB olabilir.")
        return images

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        action = cleaned.get("action")

        allowed_actions = {
            Listing.Kind.PRODUCT: {
                Listing.Action.SELL, Listing.Action.RENT, Listing.Action.SWAP, Listing.Action.WANTED
            },
            Listing.Kind.VEHICLE: {
                Listing.Action.SELL, Listing.Action.RENT, Listing.Action.SWAP, Listing.Action.WANTED
            },
            Listing.Kind.REAL_ESTATE: {
                Listing.Action.SELL, Listing.Action.RENT, Listing.Action.WANTED
            },
            Listing.Kind.SERVICE: {
                Listing.Action.SERVICE_OFFER, Listing.Action.SERVICE_REQUEST
            },
            Listing.Kind.NEED: {
                Listing.Action.WANTED, Listing.Action.SERVICE_REQUEST
            },
            Listing.Kind.JOB: {
                Listing.Action.JOB_OFFER, Listing.Action.JOB_REQUEST
            },
        }
        if kind and action and action not in allowed_actions.get(kind, set()):
            self.add_error("action", "Seçilen ilan türü için uygun bir işlem seç.")

        price_optional_actions = {
            Listing.Action.WANTED,
            Listing.Action.SERVICE_REQUEST,
            Listing.Action.JOB_REQUEST,
        }
        if (
            action not in price_optional_actions
            and not cleaned.get("price_on_request")
            and cleaned.get("price") is None
        ):
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


class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = ("amount", "message")
        labels = {"amount": "Teklif tutarı", "message": "Teklif notun"}
        widgets = {
            "message": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Teklif koşullarını ve teslim planını yaz...",
                }
            ),
            "amount": forms.NumberInput(
                attrs={"min": "0", "step": "0.01", "placeholder": "TL"}
            ),
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("body",)
        labels = {"body": "Mesajın"}
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "İlan hakkında merak ettiğini yaz...",
                    "maxlength": "1600",
                }
            )
        }

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if len(body) < 2:
            raise forms.ValidationError("Mesaj en az 2 karakter olmalıdır.")
        return body


class ListingReportForm(forms.ModelForm):
    class Meta:
        model = ListingReport
        fields = ("reason", "details")
        labels = {"reason": "Şikâyet nedeni", "details": "Açıklama"}
        widgets = {
            "details": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "İnceleme ekibimizin bilmesi gereken ayrıntıları yaz...",
                }
            )
        }
