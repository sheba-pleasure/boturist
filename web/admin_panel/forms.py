from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Material, Publication, Campaign

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['title', 'description']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10
            })
        }

class PublicationForm(forms.ModelForm):
    class Meta:
        model = Publication
        fields = ['material', 'platform', 'scheduled_time']
        widgets = {
            'scheduled_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            })
        }

class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ['name', 'description', 'start_date', 'end_date', 'status']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5
            }),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            })
        }

    def clean_target_audience(self):
        target_audience = self.cleaned_data.get('target_audience')
        if isinstance(target_audience, str):
            try:
                import json
                target_audience = json.loads(target_audience)
            except json.JSONDecodeError:
                raise forms.ValidationError(_('Invalid JSON format'))
        return target_audience

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError(_('End date must be after start date')) 