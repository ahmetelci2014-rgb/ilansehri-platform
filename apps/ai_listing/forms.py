from django import forms

from .models import AISettings


class AISettingsAdminForm(forms.ModelForm):
    class Meta:
        model = AISettings
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["provider"].help_text = (
            "Birincil sağlayıcı Google Gemini'dir. Test sağlayıcısı yalnız akış kontrolü yapar; "
            "OpenAI ve harici JSON seçenekleri yedek olarak korunur."
        )
        self.fields["model_name"].help_text = (
            "Gemini için önerilen kararlı model: gemini-3.6-flash. "
            ".env içindeki GEMINI_MODEL değeri varsa önceliklidir."
        )
        self.fields["is_enabled"].help_text = (
            "API bağlantı testi başarılı olmadan canlı kullanıcılar için açmayın."
        )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("user_daily_limit", 0) > cleaned.get("site_daily_limit", 0):
            self.add_error("user_daily_limit", "Kullanıcı limiti site geneli limitinden büyük olamaz.")
        if cleaned.get("provider") in {AISettings.Provider.GEMINI, AISettings.Provider.OPENAI} and not cleaned.get("model_name"):
            self.add_error("model_name", "Seçilen görsel analiz sağlayıcısı için model adı zorunludur.")
        return cleaned
