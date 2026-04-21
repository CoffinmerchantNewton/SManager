from django import forms
from django.conf import settings
from django.utils import timezone

from pollen.apps.workflows.models import WorkflowSchedule, WorkflowTemplate
from pollen.apps.workflows.step_library import STEP_LIBRARY


class ConsoleLoginForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "管理员密码"}))

    def clean_password(self):
        password = self.cleaned_data["password"]
        if password != settings.CONSOLE_PASSWORD:
            raise forms.ValidationError("密码不正确。")
        return password


class WorkflowTemplateForm(forms.ModelForm):
    selected_steps = forms.MultipleChoiceField(
        choices=[(name, spec["display_name"]) for name, spec in STEP_LIBRARY.items()],
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = WorkflowTemplate
        fields = ("name", "slug", "description", "region_label", "domain_codes", "default_parameters", "is_active")
        widgets = {
            "domain_codes": forms.TextInput(attrs={"placeholder": '["d01", "d02"]'}),
            "default_parameters": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["selected_steps"].initial = [step["name"] for step in self.instance.ordered_steps()]

    def clean_domain_codes(self):
        value = self.cleaned_data["domain_codes"]
        return value if isinstance(value, list) else []

    def clean_default_parameters(self):
        value = self.cleaned_data["default_parameters"]
        return value if isinstance(value, dict) else {}

    def save(self, commit=True):
        instance = super().save(commit=False)
        selected = self.cleaned_data["selected_steps"]
        steps = []
        for order, name in enumerate(selected):
            spec = STEP_LIBRARY[name]
            steps.append(
                {
                    "name": name,
                    "order": order,
                    "display_name": spec["display_name"],
                    "dependencies": spec["dependencies"],
                    "command": spec["command"],
                    "expected_outputs": spec["expected_outputs"],
                    "slurm": spec["slurm"],
                }
            )
        instance.steps = steps
        if commit:
            instance.save()
        return instance


class WorkflowScheduleForm(forms.ModelForm):
    class Meta:
        model = WorkflowSchedule
        fields = (
            "template",
            "name",
            "timezone",
            "minute",
            "hour",
            "day_of_week",
            "day_of_month",
            "month_of_year",
            "schedule_parameters",
            "enabled",
        )
        widgets = {
            "schedule_parameters": forms.Textarea(attrs={"rows": 4}),
        }


class ManualRunForm(forms.Form):
    template = forms.ModelChoiceField(queryset=WorkflowTemplate.objects.filter(is_active=True))
    business_time = forms.DateTimeField(initial=timezone.now)
