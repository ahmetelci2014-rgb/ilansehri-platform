from django import forms

from .models import ManagedActivity, ManagedRequest


SERVICE_CHOICES = (
    ("photo", "Fotoğraf / video çekimi"),
    ("listing_prep", "İlan metni ve yayın hazırlığı"),
    ("price_research", "Fiyat araştırması"),
    ("message_management", "Mesaj ve teklif yönetimi"),
    ("appointment", "Randevu / teslim koordinasyonu"),
)


class ManagedRequestForm(forms.ModelForm):
    requested_services = forms.MultipleChoiceField(
        choices=SERVICE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="İhtiyaç duyduğun hizmetler",
    )

    class Meta:
        model = ManagedRequest
        fields = ("package", "requested_services", "preferred_contact", "customer_notes")
        labels = {"customer_notes": "Bize anlatmak istediğin ayrıntılar"}
        widgets = {"customer_notes": forms.Textarea(attrs={"rows": 6})}


class ManagedStaffForm(forms.ModelForm):
    class Meta:
        model = ManagedRequest
        fields = (
            "assigned_staff",
            "status",
            "package",
            "quote_amount",
            "success_fee_percent",
            "progress",
            "next_action",
            "scheduled_at",
            "internal_notes",
        )
        widgets = {
            "progress": forms.NumberInput(attrs={"min": 0, "max": 100}),
            "internal_notes": forms.Textarea(attrs={"rows": 5}),
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class ManagedActivityForm(forms.ModelForm):
    class Meta:
        model = ManagedActivity
        fields = ("activity_type", "note", "visible_to_customer")
        widgets = {"note": forms.Textarea(attrs={"rows": 4})}
