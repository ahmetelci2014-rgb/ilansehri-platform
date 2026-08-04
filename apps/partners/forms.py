from django import forms

from apps.listings.locations import CITY_CHOICES

from .models import PartnerProfile, Task, TaskApplication

SKILL_CHOICES = (
    ("photo", "Fotoğraf / video"),
    ("listing", "İlan hazırlama"),
    ("price", "Fiyat araştırması"),
    ("communication", "Müşteri iletişimi"),
    ("appointment", "Randevu / saha desteği"),
)


class PartnerProfileForm(forms.ModelForm):
    skills = forms.MultipleChoiceField(choices=SKILL_CHOICES, widget=forms.CheckboxSelectMultiple)
    service_cities = forms.MultipleChoiceField(choices=CITY_CHOICES, widget=forms.SelectMultiple)

    class Meta:
        model = PartnerProfile
        fields = ("about", "skills", "service_cities", "available")
        labels = {
            "about": "Deneyimini ve neden görev ortağı olmak istediğini anlat",
            "available": "Yeni görev almaya uygunum",
        }
        widgets = {"about": forms.Textarea(attrs={"rows": 6})}


class TaskApplicationForm(forms.ModelForm):
    class Meta:
        model = TaskApplication
        fields = ("note",)
        labels = {"note": "Görev için kısa notun"}
        widgets = {"note": forms.Textarea(attrs={"rows": 4, "placeholder": "Uygunluk, deneyim ve planını yaz..."})}


class TaskSubmissionForm(forms.ModelForm):
    ALLOWED_PROOF_TYPES = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    }
    MAX_PROOF_SIZE = 10 * 1024 * 1024

    class Meta:
        model = Task
        fields = ("result_note", "proof_file")
        labels = {"result_note": "Yapılan çalışma", "proof_file": "Kanıt / teslim dosyası"}
        widgets = {
            "result_note": forms.Textarea(attrs={"rows": 6}),
            "proof_file": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp,application/pdf"}),
        }

    def clean_proof_file(self):
        proof_file = self.cleaned_data.get("proof_file")
        if not proof_file:
            return proof_file
        if proof_file.size > self.MAX_PROOF_SIZE:
            raise forms.ValidationError("Teslim dosyası en fazla 10 MB olabilir.")
        content_type = getattr(proof_file, "content_type", "")
        if content_type not in self.ALLOWED_PROOF_TYPES:
            raise forms.ValidationError("Yalnız JPG, PNG, WEBP veya PDF dosyası yükleyebilirsiniz.")
        return proof_file


class TaskCreateForm(forms.ModelForm):
    city = forms.ChoiceField(choices=(("", "Şehir seçin"), *CITY_CHOICES), label="Şehir")

    class Meta:
        model = Task
        fields = (
            "title",
            "task_type",
            "description",
            "city",
            "district",
            "min_level",
            "reward",
            "success_bonus",
            "due_at",
        )
        labels = {
            "title": "Görev başlığı",
            "task_type": "Görev türü",
            "description": "Açıklama ve teslim ölçütleri",
            "district": "İlçe",
            "min_level": "Minimum ortak seviyesi",
            "reward": "Sabit görev kazancı",
            "success_bonus": "Başarı bonusu",
            "due_at": "Son teslim zamanı",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "due_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "reward": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "success_bonus": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }
