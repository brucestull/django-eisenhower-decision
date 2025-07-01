# decide/forms.py
from django import forms

from .models import Decision


class DecisionForm(forms.ModelForm):
    class Meta:
        model = Decision
        fields = ["title", "description"]


class DecisionResponseForm(forms.Form):
    answer = forms.TypedChoiceField(
        coerce=lambda x: x == "True",
        choices=[("True", "Yes"), ("False", "No")],
        widget=forms.RadioSelect(attrs={"class": "sr-only"}),
        label="",
    )
