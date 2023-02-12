from django import forms
from .models import Measurements, Project

YEARS = [x for x in range(2021,2023)]

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ('name','contact_name','contact_email')

class MeasurementsForm(forms.ModelForm):
    measure_date = forms.DateField(label='Measurement date', initial="2022-01-01",
                                   widget=forms.SelectDateWidget(years=YEARS))
    datafile = forms.FileField(label='Data file')
    fieldfile = forms.FileField(label='Field form')

    class Meta:
        model = Measurements
        fields = ('soil','chamber','device','project','fftype','comment')

    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.fields['project'].queryset = Project.objects.all()

class ChangeRecordForm(forms.Form):
    new_measure_date = forms.DateField(label='Measurement date', initial="2022-01-01",
                                       widget=forms.SelectDateWidget(years=YEARS))
    new_comment = forms.CharField(max_length=255,required=False)
    new_soil = forms.ChoiceField(choices=Measurements.SOIL_CHOICES)

    new_project = forms.ModelChoiceField(queryset=Project.objects.none())

    def __init__(self, *args, **kwargs):
        super(ChangeRecordForm, self).__init__(*args,**kwargs)
        self.fields['new_project'].queryset = Project.objects.all()
