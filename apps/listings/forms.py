from django import forms
from .models import Listing


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = [
            "kind", "action", "management_mode", "category", "title", "description",
            "price", "price_on_request", "condition", "city", "district", "neighborhood",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
        }
