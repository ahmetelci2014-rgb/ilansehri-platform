from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from apps.listings.locations import CITY_CHOICES

from .models import User, VerificationCode


class SignUpForm(UserCreationForm):
    accept_terms = forms.BooleanField(
        label="Üyelik koşullarını ve KVKK aydınlatma metnini kabul ediyorum",
    )
    city = forms.ChoiceField(
        choices=(("", "Şehir seçin"), *CITY_CHOICES),
        required=False,
        label="Şehir",
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "city",
            "district",
            "user_type",
            "accepts_marketing",
            "password1",
            "password2",
        )
        widgets = {
            "username": forms.TextInput(attrs={"autocomplete": "username"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"placeholder": "05xx xxx xx xx"}),
            "district": forms.TextInput(attrs={"placeholder": "İlçe"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu e-posta adresiyle daha önce hesap açılmış.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.terms_accepted_at = timezone.now()
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    city = forms.ChoiceField(
        choices=(("", "Şehir seçin"), *CITY_CHOICES),
        required=False,
        label="Şehir",
    )

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "user_type",
            "city",
            "district",
            "neighborhood",
            "bio",
            "avatar",
            "accepts_marketing",
        )
        labels = {
            "bio": "Kendini veya işletmeni tanıt",
            "avatar": "Profil fotoğrafı",
            "accepts_marketing": "Kampanya ve yenilik bildirimlerini almak istiyorum",
        }
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 5, "placeholder": "Kısa ve güven veren bir tanıtım yaz..."}),
            "phone": forms.TextInput(attrs={"placeholder": "05xx xxx xx xx"}),
            "district": forms.TextInput(attrs={"placeholder": "İlçe"}),
            "neighborhood": forms.TextInput(attrs={"placeholder": "Mahalle"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Bu e-posta adresi başka bir hesapta kullanılıyor.")
        return email


class VerificationStartForm(forms.Form):
    channel = forms.ChoiceField(choices=VerificationCode.Channel.choices, label="Doğrulama yöntemi")

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_channel(self):
        channel = self.cleaned_data["channel"]
        if channel == VerificationCode.Channel.PHONE and not self.user.phone:
            raise forms.ValidationError("Önce profilinden telefon numaranı ekle.")
        if channel == VerificationCode.Channel.EMAIL and not self.user.email:
            raise forms.ValidationError("Önce profilinden e-posta adresini ekle.")
        return channel


class VerificationConfirmForm(forms.Form):
    channel = forms.ChoiceField(choices=VerificationCode.Channel.choices, widget=forms.HiddenInput)
    code = forms.CharField(
        min_length=6,
        max_length=6,
        label="6 haneli doğrulama kodu",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code"}),
    )


class AccountClosureForm(forms.Form):
    password = forms.CharField(
        label="Mevcut şifren",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    reason = forms.CharField(
        required=False,
        max_length=1000,
        label="Hesabını kapatmak isteme nedenin",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "İsteğe bağlı olarak kısa bir açıklama yazabilirsin."}),
    )
    confirmation = forms.BooleanField(
        label="Hesap kapatma talebimin inceleneceğini ve bu süreçte hesabımın açık kalacağını anlıyorum.",
    )

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Şifren doğru değil.")
        return password
