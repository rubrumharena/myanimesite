from django import forms
from django.shortcuts import reverse


class FilterRadioSelect(forms.RadioSelect):
    def __init__(self, *args, title_id=None, **kwargs):
        self.title_id = title_id
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        option['attrs']['class'] = f'sr-only peer/{value}'

        if self.title_id is not None:
            option['attrs']['data-url'] = (
                reverse(
                    'comments:comments',
                    kwargs={
                        'title_id': self.title_id,
                    },
                )
                + f'?filter_by={value}'
            )
        return option


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
        option['attrs']['data-status-input'] = ''
        if self.title_id is not None:
            option['attrs']['data-url'] = reverse(
                'titles:set_status',
                kwargs={
                    'title_id': self.title_id,
                    'status': value,
                },
            )
        return option
