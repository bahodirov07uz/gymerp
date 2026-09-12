from django import forms

from .models import Member

INPUT_CLS = "w-full border rounded-lg px-3 py-2"


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            "first_name", "last_name", "phone", "date_of_birth",
            "gender", "address", "notes", "photo", "is_active",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date", "class": INPUT_CLS}),
            "notes": forms.Textarea(attrs={"rows": 2, "class": INPUT_CLS}),
            "first_name": forms.TextInput(attrs={"class": INPUT_CLS}),
            "last_name": forms.TextInput(attrs={"class": INPUT_CLS}),
            "phone": forms.TextInput(attrs={"class": INPUT_CLS, "placeholder": "+998..."}),
            "gender": forms.Select(attrs={"class": INPUT_CLS}),
            "address": forms.TextInput(attrs={"class": INPUT_CLS}),
            "photo": forms.ClearableFileInput(attrs={
                "class": INPUT_CLS,
                "accept": "image/*",
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
        }


class MemberPhotoForm(forms.ModelForm):
    """Profildan rasmni alohida yangilash uchun kichik forma.

    ModelForm validatsiyasi Member.clean() dagi 5MB chegarani
    avtomatik tekshiradi.
    """

    class Meta:
        model = Member
        fields = ["photo"]
        widgets = {
            "photo": forms.ClearableFileInput(attrs={
                "class": INPUT_CLS,
                "accept": "image/*",
            }),
        }
