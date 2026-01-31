from django import forms

from common.utils.validators import validate_rating, validate_years
from lists.models import Collection
from titles.models import TitleCreationHistory


class TitleForm(forms.ModelForm):
    ANY = ''
    SERIES = True
    MOVIE = False
    IS_SERIES = (
        (ANY, '---'),
        (SERIES, 'Сериал'),
        (MOVIE, 'Фильм'),
    )

    limit = forms.IntegerField(
        widget=forms.TextInput(
            attrs={
                'class': 'input-field',
            }
        ),
        min_value=1,
        max_value=250,
        initial=1,
    )
    page = forms.IntegerField(
        widget=forms.TextInput(
            attrs={
                'class': 'input-field',
            }
        ),
        min_value=1,
        initial=1,
    )
    rating = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'input-field',
            }
        ),
        required=False,
        validators=[validate_rating],
    )
    year = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'input-field',
            }
        ),
        required=False,
        validators=[validate_years],
    )

    genre = forms.ChoiceField(required=False)
    is_series = forms.ChoiceField(required=False, choices=IS_SERIES)
    sequels = forms.BooleanField(required=False, widget=forms.CheckboxInput())

    class Meta:
        model = TitleCreationHistory
        exclude = ('created_at',)

    def __init__(self, *args, **kwargs):
        super(TitleForm, self).__init__(*args, **kwargs)
        self.fields['genre'].choices = [('', '---')] + list(
            Collection.objects.filter(type=Collection.GENRE).values_list('slug', 'name')
        )
