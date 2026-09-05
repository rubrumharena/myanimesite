from django import forms
from django.utils.translation import gettext_lazy as _

from common.utils.forms import StatusRadioSelect
from common.utils.validators import validate_rating, validate_years
from lists.models import Collection
from titles.models import LibraryEntry, Title, TitleImportLog


class TitleForm(forms.ModelForm):
    ANY = ''
    SERIES = True
    MOVIE = False
    IS_SERIES = (
        (ANY, '---'),
        (SERIES, _('Сериал')),
        (MOVIE, _('Фильм')),
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
        model = TitleImportLog
        exclude = ('created_at',)

    def __init__(self, *args, **kwargs):
        super(TitleForm, self).__init__(*args, **kwargs)
        self.fields['genre'].choices = [('', '---')] + list(
            Collection.objects.filter(type=Collection.GENRE).values_list('slug', 'name')
        )


class StatusForm(forms.ModelForm):
    BASE_CLASSES = 'flex items-center justify-between gap-3 h-9 px-3 rounded-lg cursor-pointer text-sm font-bold !text-neutral-400 hover:bg-neutral-400/10 hover:!text-white'
    STATUS_LABEL_CLASSES = {
        'not_watched': f'{BASE_CLASSES} peer-checked/not-watched:bg-neutral-400/10 peer-checked/not-watched:!text-neutral-400',
        'current': f'{BASE_CLASSES} peer-checked/current:bg-cyan-400/10 peer-checked/current:!text-cyan-400',
        'planned': f'{BASE_CLASSES} peer-checked/planned:bg-pink-500/10 peer-checked/planned:!text-pink-500',
        'watched': f'{BASE_CLASSES} peer-checked/watched:bg-green-500/10 peer-checked/watched:!text-green-500',
        'skipped': f'{BASE_CLASSES} peer-checked/skipped:bg-red-500/10 peer-checked/skipped:!text-red-500',
    }

    title = forms.ModelChoiceField(queryset=Title.objects.all())
    status = forms.ChoiceField(choices=LibraryEntry.STATUS_CHOICES, widget=StatusRadioSelect())

    class Meta:
        model = LibraryEntry
        exclude = ('user',)
