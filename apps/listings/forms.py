from django import forms

from .models import Listing, Offer


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
            "city",
            "district",
            "neighborhood",
        ]
        labels = {
            "kind": "İlan türü",
            "action": "Ne yapmak istiyorsun?",
            "management_mode": "İlanı kim yönetecek?",
            "condition": "Ürün / hizmet durumu",
            "price_on_request": "Fiyat yerine teklif almak istiyorum",
            "category": "Kategori",
            "price": "Fiyat",
            "city": "Şehir",
            "district": "İlçe",
            "neighborhood": "Mahalle",
        }
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "rows": 7,
                    "placeholder": "Ürün, hizmet veya ihtiyacını ayrıntılı anlat. Ölçü, özellik, teslim ve kullanım durumunu ekle...",
                }
            ),
            "title": forms.TextInput(
                attrs={"placeholder": "Örn. Az kullanılmış iPhone 15 Pro 256 GB"}
            ),
            "price": forms.NumberInput(
                attrs={"min": "0", "step": "0.01", "placeholder": "0,00"}
            ),
            "condition": forms.TextInput(
                attrs={"placeholder": "Örn. Sıfır, az kullanılmış, iyi durumda"}
            ),
            "city": forms.TextInput(attrs={"placeholder": "Örn. Şanlıurfa"}),
            "district": forms.TextInput(attrs={"placeholder": "Örn. Karaköprü"}),
            "neighborhood": forms.TextInput(attrs={"placeholder": "Mahalle (isteğe bağlı)"}),
        }

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
        if not cleaned.get("price_on_request") and cleaned.get("price") is None:
            self.add_error("price", "Fiyat gir veya teklif almak istediğini işaretle.")
        return cleaned


class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = ("amount", "message")
        labels = {"amount": "Teklif tutarı", "message": "Mesajın"}
        widgets = {
            "message": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Teklif koşullarını ve teslim planını yaz..."}
            ),
            "amount": forms.NumberInput(
                attrs={"min": "0", "step": "0.01", "placeholder": "TL"}
            ),
        }
