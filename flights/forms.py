from django import forms
from django.utils import timezone

from .models import Airline, City


class FlightSearchForm(forms.Form):
    TRIP_CHOICES = [('oneway', 'ცალმხრივი'), ('return', 'ორმხრივი')]
    CABIN_CHOICES = [('economy', 'ეკონომ კლასი'), ('business', 'ბიზნეს კლასი')]
    SORT_CHOICES = [
        ('departure_time', 'თარიღით'),
        ('economy_price', 'ფასით (იაფი → ძვირი)'),
        ('-economy_price', 'ფასით (ძვირი → იაფი)'),
    ]

    trip_type = forms.ChoiceField(label='მგზავრობის ტიპი', choices=TRIP_CHOICES, required=False,
                                  initial='oneway', widget=forms.RadioSelect)
    cabin = forms.ChoiceField(label='კლასი', choices=CABIN_CHOICES, required=False,
                              initial='economy', widget=forms.RadioSelect)
    origin = forms.ModelChoiceField(label='საიდან', queryset=City.objects.all(), required=False, empty_label='საიდან')
    destination = forms.ModelChoiceField(label='სად', queryset=City.objects.all(), required=False, empty_label='სად')
    date = forms.DateField(label='გაფრენის თარიღი', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    return_date = forms.DateField(label='დაბრუნების თარიღი', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    airline = forms.ModelChoiceField(label='ავიაკომპანია', queryset=Airline.objects.all(), required=False, empty_label='ყველა')
    max_price = forms.IntegerField(label='მაქს. ფასი (₾)', required=False, min_value=0)
    direct_only = forms.BooleanField(label='მხოლოდ პირდაპირი', required=False)
    sort = forms.ChoiceField(label='დალაგება', choices=SORT_CHOICES, required=False)

    def clean(self):
        data = super().clean()
        # ორმხრივზე დაბრუნების თარიღი აუცილებელია
        if data.get('trip_type') == 'return':
            go = data.get('date')
            back = data.get('return_date')
            if not back:
                self.add_error('return_date', 'მიუთითე დაბრუნების თარიღი')
            elif go and back < go:
                self.add_error('return_date', 'დაბრუნება გაფრენამდე ვერ იქნება')
        return data

    @property
    def is_return(self):
        return self.is_bound and self.data.get('trip_type') == 'return'


class CheckInForm(forms.Form):
    pnr = forms.CharField(label='ბილეთის (ჯავშნის) ნომერი', min_length=6, max_length=6,
                          widget=forms.TextInput(attrs={'placeholder': 'მაგ. K7XQ2M', 'autocomplete': 'off'}))
    last_name = forms.CharField(label='მგზავრის გვარი', max_length=50)

    def clean_pnr(self):
        # პატარა ასოებით შეყვანილიც იმუშავებს
        return self.cleaned_data['pnr'].strip().upper()


class PaymentForm(forms.Form):
    """ფიქტიური გადახდა. ბარათის მონაცემები არ ინახება — მხოლოდ ბოლო 4 ციფრი."""
    card_name = forms.CharField(label='ბარათის მფლობელი', max_length=60,
                                widget=forms.TextInput(attrs={'placeholder': 'GIORGI BERIDZE'}))
    card_number = forms.CharField(label='ბარათის ნომერი', max_length=23,
                                  widget=forms.TextInput(attrs={'placeholder': '4242 4242 4242 4242', 'data-card': 'number'}))
    expiry = forms.CharField(label='ვადა (MM/YY)', max_length=5,
                             widget=forms.TextInput(attrs={'placeholder': '12/28', 'data-card': 'expiry'}))
    cvv = forms.CharField(label='CVV', max_length=4, widget=forms.PasswordInput(attrs={'placeholder': '•••'}))

    def clean_card_number(self):
        number = self.cleaned_data['card_number'].replace(' ', '').replace('-', '')
        # ფიქტიური გადახდა: მიიღება ნებისმიერი ბარათი — ვამოწმებთ მხოლოდ, რომ 13-19 ციფრია
        if not number.isdigit() or len(number) < 13 or len(number) > 19:
            raise forms.ValidationError('ბარათის ნომერი უნდა იყოს 13-19 ციფრი')
        return number

    def clean_expiry(self):
        value = self.cleaned_data['expiry'].strip()
        parts = value.split('/')
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit() or len(parts[1]) != 2:
            raise forms.ValidationError('ფორმატი: MM/YY')

        month = int(parts[0])
        year = 2000 + int(parts[1])
        if month < 1 or month > 12:
            raise forms.ValidationError('ფორმატი: MM/YY')

        today = timezone.localdate()
        if year < today.year or (year == today.year and month < today.month):
            raise forms.ValidationError('ბარათს ვადა გაუვიდა')
        return value

    def clean_cvv(self):
        cvv = self.cleaned_data['cvv'].strip()
        if not cvv.isdigit() or len(cvv) not in (3, 4):
            raise forms.ValidationError('CVV — 3 ციფრი')
        return cvv
