from django import forms

from .models import Airline, City


class CheckInForm(forms.Form):
    pnr = forms.CharField(label='ბილეთის (ჯავშნის) ნომერი', max_length=6, min_length=6,
                          widget=forms.TextInput(attrs={'placeholder': 'მაგ. K7XQ2M', 'autocomplete': 'off'}))
    last_name = forms.CharField(label='მგზავრის გვარი', max_length=50)

    def clean_pnr(self):
        return self.cleaned_data['pnr'].strip().upper()


def luhn_valid(number):
    """ბარათის ნომრის შემოწმება Luhn-ის ალგორითმით."""
    total = 0
    for i, ch in enumerate(reversed(number)):
        d = int(ch)
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


class PaymentForm(forms.Form):
    """ფიქტიური გადახდა — ბარათის მონაცემები არსად ინახება (მხოლოდ ბოლო 4 ციფრი)."""
    card_name = forms.CharField(label='ბარათის მფლობელი', max_length=60,
                                widget=forms.TextInput(attrs={'placeholder': 'GIORGI BERIDZE', 'autocomplete': 'cc-name'}))
    card_number = forms.CharField(label='ბარათის ნომერი', max_length=23,
                                  widget=forms.TextInput(attrs={'placeholder': '4242 4242 4242 4242', 'inputmode': 'numeric',
                                                                'autocomplete': 'cc-number', 'data-card': 'number'}))
    expiry = forms.CharField(label='ვადა (MM/YY)', max_length=5,
                             widget=forms.TextInput(attrs={'placeholder': '12/28', 'inputmode': 'numeric',
                                                           'autocomplete': 'cc-exp', 'data-card': 'expiry'}))
    cvv = forms.CharField(label='CVV', max_length=4,
                          widget=forms.PasswordInput(attrs={'placeholder': '•••', 'inputmode': 'numeric', 'autocomplete': 'cc-csc'}))

    def clean_card_number(self):
        number = ''.join(self.cleaned_data['card_number'].split()).replace('-', '')
        if not number.isdigit() or not 13 <= len(number) <= 19 or not luhn_valid(number):
            raise forms.ValidationError('ბარათის ნომერი არასწორია')
        return number

    def clean_expiry(self):
        import re
        from django.utils import timezone
        value = self.cleaned_data['expiry'].strip()
        m = re.fullmatch(r'(\d{2})/(\d{2})', value)
        if not m or not 1 <= int(m[1]) <= 12:
            raise forms.ValidationError('ფორმატი: MM/YY')
        today = timezone.localdate()
        if (2000 + int(m[2]), int(m[1])) < (today.year, today.month):
            raise forms.ValidationError('ბარათს ვადა გაუვიდა')
        return value

    def clean_cvv(self):
        cvv = self.cleaned_data['cvv'].strip()
        if not cvv.isdigit() or len(cvv) not in (3, 4):
            raise forms.ValidationError('CVV — 3 ციფრი')
        return cvv


class FlightSearchForm(forms.Form):
    ONE_WAY = 'oneway'
    RETURN = 'return'
    TRIP_CHOICES = [(ONE_WAY, 'ცალმხრივი'), (RETURN, 'ორმხრივი')]

    SORT_CHOICES = [
        ('departure_time', 'თარიღით'),
        ('economy_price', 'ფასით (იაფი → ძვირი)'),
        ('-economy_price', 'ფასით (ძვირი → იაფი)'),
    ]

    CABIN_CHOICES = [('economy', 'ეკონომ კლასი'), ('business', 'ბიზნეს კლასი')]

    trip_type = forms.ChoiceField(choices=TRIP_CHOICES, required=False, initial=ONE_WAY,
                                  widget=forms.RadioSelect, label='მგზავრობის ტიპი')
    cabin = forms.ChoiceField(choices=CABIN_CHOICES, required=False, initial='economy',
                              widget=forms.RadioSelect, label='კლასი')
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
