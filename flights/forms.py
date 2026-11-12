from django import forms

from .models import Airline, City


class FlightSearchForm(forms.Form):
    SORT_CHOICES = [
        ('departure_time', 'თარიღით'),
        ('economy_price', 'ფასით (იაფი → ძვირი)'),
        ('-economy_price', 'ფასით (ძვირი → იაფი)'),
    ]

    origin = forms.ModelChoiceField(City.objects.all(), required=False, label='საიდან', empty_label='ყველა')
    destination = forms.ModelChoiceField(City.objects.all(), required=False, label='სად', empty_label='ყველა')
    date = forms.DateField(required=False, label='თარიღი', widget=forms.DateInput(attrs={'type': 'date'}))
    airline = forms.ModelChoiceField(Airline.objects.all(), required=False, label='ავიაკომპანია', empty_label='ყველა')
    max_price = forms.IntegerField(required=False, min_value=0, label='მაქს. ფასი (₾)')
    direct_only = forms.BooleanField(required=False, label='მხოლოდ პირდაპირი')
    sort = forms.ChoiceField(choices=SORT_CHOICES, required=False, label='დალაგება')
