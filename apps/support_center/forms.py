from django import forms

from apps.accounts.models import User
from apps.listings.models import Listing, Transaction

from .models import SupportReply, SupportTicket


class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ("category", "subject", "description", "related_listing", "related_transaction")
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "rows": 7,
                    "placeholder": "Sorunu, gördüğün hata mesajını ve denediğin adımları ayrıntılı şekilde yaz.",
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["related_listing"].required = False
        self.fields["related_transaction"].required = False
        self.fields["related_listing"].empty_label = "İlanla ilgili değil"
        self.fields["related_transaction"].empty_label = "İşlemle ilgili değil"
        if user and user.is_authenticated:
            listing_ids = set(user.listings.values_list("id", flat=True))
            transaction_qs = Transaction.objects.filter(buyer=user) | Transaction.objects.filter(seller=user)
            transaction_ids = set(transaction_qs.values_list("id", flat=True))
            listing_ids.update(transaction_qs.values_list("listing_id", flat=True))
            self.fields["related_listing"].queryset = Listing.objects.filter(id__in=listing_ids).order_by("-updated_at")
            self.fields["related_transaction"].queryset = Transaction.objects.filter(id__in=transaction_ids).select_related("listing")
        else:
            self.fields["related_listing"].queryset = Listing.objects.none()
            self.fields["related_transaction"].queryset = Transaction.objects.none()

    def clean(self):
        cleaned = super().clean()
        listing = cleaned.get("related_listing")
        transaction = cleaned.get("related_transaction")
        if transaction and listing and transaction.listing_id != listing.id:
            self.add_error("related_listing", "Seçilen ilan, seçilen işlemle eşleşmiyor.")
        return cleaned


class SupportReplyForm(forms.ModelForm):
    class Meta:
        model = SupportReply
        fields = ("message",)
        widgets = {
            "message": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Yanıtını buraya yaz..."}
            )
        }


class StaffTicketUpdateForm(forms.ModelForm):
    public_reply = forms.CharField(
        required=False,
        label="Kullanıcıya yanıt",
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Kullanıcının göreceği yanıt..."}),
    )
    internal_note = forms.CharField(
        required=False,
        label="Ekip içi not",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Yalnız yönetim ekibinin göreceği not..."}),
    )

    class Meta:
        model = SupportTicket
        fields = ("status", "priority", "assigned_to")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(is_staff=True, is_active=True).order_by("first_name", "username")
        self.fields["assigned_to"].required = False
