from django import forms

from .models import Airline, City


class FlightSearchForm(forms.Form):
    ONE_WAY = 'oneway'
    RETURN = 'return'
    TRIP_CHOICES = [(ONE_WAY, 'ცალმხრივი'), (RETURN, 'ორმხრივი')]

    SORT_CHOICES = [
        ('departure_time', 'თარიღით'),
        ('economy_price', 'ფასით (იაფი → ძვირი)'),
        ('-economy_price', 'ფასით (ძვირი → იაფი)'),
    ]

    trip_type = forms.ChoiceField(choices=TRIP_CHOICES, required=False, initial=ONE_WAY,
                                  widget=forms.RadioSelect, label='მგზავრობის ტიპი')
    origin = forms.ModelChoiceField(City.objects.all(), required=False, label='საიდან', empty_label='საიდან')
    destination = forms.ModelChoiceField(City.objects.all(), required=False, label='სად', empty_label='სად')
    date = forms.DateField(required=False, label='გაფრენის თარიღი', widget=forms.DateInput(attrs={'type': 'date'}))
    return_date = forms.DateField(required=False, label='დაბრუნების თარიღი', widget=forms.DateInput(attrs={'type': 'date'}))
    airline = forms.ModelChoiceField(Airline.objects.all(), required=False, label='ავიაკომპანია', empty_label='ყველა')
    max_price = forms.IntegerField(required=False, min_value=0, label='მაქს. ფასი (₾)')
    direct_only = forms.BooleanField(required=False, label='მხოლოდ პირდაპირი')
    sort = forms.ChoiceField(choices=SORT_CHOICES, required=False, label='დალაგება')

    def clean(self):
        data = super().clean()
        if data.get('trip_type') == self.RETURN:
            if not data.get('return_date'):
                self.add_error('return_date', 'მიუთითე დაბრუნების თარიღი')
            elif data.get('date') and data['return_date'] < data['date']:
                self.add_error('return_date', 'დაბრუნება გაფრენამდე ვერ იქნება')
        return data

    @property
    def is_return(self):
        return self.is_bound and self.data.get('trip_type') == self.RETURN
