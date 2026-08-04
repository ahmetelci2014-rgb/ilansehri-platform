from django import forms

from .models import AISettings


class AISettingsAdminForm(forms.ModelForm):
    class Meta:
        model = AISettings
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("user_daily_limit", 0) > cleaned.get("site_daily_limit", 0):
            self.add_error("user_daily_limit", "Kullanıcı limiti site geneli limitinden büyük olamaz.")
        return cleaned
