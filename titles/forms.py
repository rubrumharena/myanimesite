from django import forms
from django.shortcuts import reverse

from common.utils.validators import validate_rating, validate_years
from lists.models import Collection
from titles.models import TitleImportLog, TitleStatus, Title


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
        model = TitleImportLog
        exclude = ('created_at',)

    def __init__(self, *args, **kwargs):
        super(TitleForm, self).__init__(*args, **kwargs)
        self.fields['genre'].choices = [('', '---')] + list(
            Collection.objects.filter(type=Collection.GENRE).values_list('slug', 'name')
        )


class StatusRadioSelect(forms.RadioSelect):
    def __init__(self, *args, title_id=None, **kwargs):
        self.title_id = title_id
        super().__init__(*args, **kwargs)

    peer_name_map = {
        'not_watched': 'not-watched',
        'current': 'current',
        'planned': 'planned',
        'watched': 'watched',
        'skipped': 'skipped',
    }

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        peer_name = self.peer_name_map.get(value, value)
        option['attrs']['class'] = f'sr-only peer/{peer_name}'
        option['attrs']['data-chart'] = peer_name
        if self.title_id is not  None:
            option['attrs']['data-url'] = reverse('titles:set_status', kwargs={
                'title_id': self.title_id,
                'status': value,
            })
        return option


class StatusForm(forms.ModelForm):
    BASE_CLASSES = 'flex items-center justify-between gap-3 h-9 px-3 rounded-lg cursor-pointer text-sm font-bold !text-neutral-400 transition- hover:bg-neutral-400/10 hover:!text-white'
    STATUS_LABEL_CLASSES = {
        'not_watched': f'{BASE_CLASSES} peer-checked/not-watched:bg-neutral-400/10 peer-checked/not-watched:!text-neutral-400',
        'current': f'{BASE_CLASSES} peer-checked/current:bg-cyan-400/10 peer-checked/current:!text-cyan-400',
        'planned': f'{BASE_CLASSES} peer-checked/planned:bg-pink-500/10 peer-checked/planned:!text-pink-500',
        'watched': f'{BASE_CLASSES} peer-checked/watched:bg-green-500/10 peer-checked/watched:!text-green-500',
        'skipped': f'{BASE_CLASSES} peer-checked/skipped:bg-red-500/10 peer-checked/skipped:!text-red-500',
    }

    title = forms.ModelChoiceField(queryset=Title.objects.all())
    status = forms.ChoiceField(choices=TitleStatus.STATUS_CHOICES,
                               widget=StatusRadioSelect())

    class Meta:
        model = TitleStatus
        exclude = ('user',)
