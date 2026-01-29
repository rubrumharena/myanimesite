import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from http import HTTPStatus
from typing import List, Optional, Any, Dict


def generate_years_and_decades(expand_range: Optional[int]=None, current: bool=False) -> List[str]:
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


def get_partial_fill(rating: float | int, stars: int=10) -> Dict[int, int]:
    rating = float(rating)
    stars = int(stars)
    if rating > stars:
        raise ValueError('The number must equal or less than the number of stars')
    if rating < 0:
        raise ValueError('The number must be positive')
    filled_rating = {}
    full_stars = int(rating)

    partial = int(round((rating - full_stars) * 100))

    for star in range(1, stars + 1):
        if star <= full_stars:
            filled_rating[star] = 100
        elif star == full_stars + 1 and partial:
            filled_rating[star] = partial
        else:
            filled_rating[star] = 0

    return filled_rating


def generate_gradient() -> str:
    gradients = [
        'background: linear-gradient(to right, #00b0ff 10%, #00e5ff 30%, #00b8d4 50%, #008ba3 70%, #004d6f 90%);',
        'background: radial-gradient(circle at center, #00ff84 0%, #00e676 20%, #76ff03 55%, #64dd17 80%, #1b5e20 100%);',
        'background: conic-gradient(from 90deg at center, #ff00ff 0%, #9b00e6 25%, #6200e6 50%, #2e00b3 75%, #004d99 100%);',
        'background: linear-gradient(to bottom right, #ee0979 5%, #ff6a00 25%, #f5b700 55%, #ffcb05 75%, #b5d900 95%);',
        'background: radial-gradient(ellipse farthest-corner at 40% 40%, #a16eff 0%, #b36eff 25%, #e500b3 50%, #ff00b3 75%, #8a00e6 100%);',
        'background: conic-gradient(from 0deg at 50% 50%, #00ffff 0%, #00b3b3 30%, #009999 50%, #006666 75%, #003333 100%);',
        'background: linear-gradient(to top, #d9a7c7 10%, #ff7eb3 35%, #ff6ec7 55%, #ff0044 75%, #9c004c 95%);',
        'background: radial-gradient(circle farthest-corner at 60% 40%, #00d4ff 0%, #ff007f 25%, #f50057 50%, #8e2de2 75%, #4a00e0 100%);',
        'background: linear-gradient(120deg, #9b59b6 0%, #8e44ad 30%, #3498db 50%, #2980b9 70%, #1d73b7 100%);',
        'background: conic-gradient(from 180deg at top left, #ffcc00 0%, #ff6600 30%, #ff0000 50%, #b30000 75%, #800000 100%);',
        'background: linear-gradient(to left, #ff5c8f 0%, #ff0088 20%, #ff0055 45%, #b10000 70%, #7a0000 95%);',
        'background: radial-gradient(ellipse at bottom right, #ea3ad9 0%, #c92be7 25%, #6b2be7 50%, #3b82f6 75%, #00d4ff 100%);',
    ]
    return random.choice(gradients)
