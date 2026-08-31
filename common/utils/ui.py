import random
from datetime import datetime


_COVERS = (
    ('#22d3ee', '#0d9488', '#134e4a'),  # циан → тил
    ('#2dd4bf', '#0284c7', '#0c4a6e'),  # тил → небесный
    ('#38bdf8', '#2563eb', '#1e3a8a'),  # небесный → синий
    ('#818cf8', '#7c3aed', '#4c1d95'),  # индиго → фиолетовый
    ('#c084fc', '#4f46e5', '#312e81'),  # пурпурный → индиго
    ('#a78bfa', '#c026d3', '#701a75'),  # фиолетовый → фуксия
    ('#e879f9', '#db2777', '#831843'),  # фуксия → розовый
    ('#f472b6', '#e11d48', '#881337'),  # розовый → малиновый
    ('#fb7185', '#ea580c', '#7c2d12'),  # малиновый → оранжевый
    ('#fbbf24', '#d97706', '#78350f'),  # янтарный
    ('#a3e635', '#059669', '#064e3b'),  # лаймовый → изумрудный
    ('#34d399', '#0891b2', '#164e63'),  # изумрудный → циан
)


def generate_years_and_decades(expand_range: int | None = None, current: bool = False) -> list[str]:
    current_year = datetime.now().year
    current_decade = current_year // 10 * 10
    step = -10
    end = 1950
    expand_range = current_year - expand_range if expand_range is not None else current_decade

    expanded_cur_decade = list(map(str, list(range(current_year + (0 if current else 3), expand_range - 1, -1))))
    decades = []
    for start_year in range(current_decade, end, step):
        end_year = current_year + 3 if start_year == current_decade else start_year + 9
        decades.append(f'{start_year}-{end_year}')
    return expanded_cur_decade + decades


def generate_gradient() -> str:
    light, mid, deep = random.choice(_COVERS)
    return f'background: linear-gradient(150deg, {light} 0%, {mid} 45%, {deep} 100%);'
