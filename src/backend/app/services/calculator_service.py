"""CPU tier calculator service — stateless, no DB access.

Conversion logic:
  hp → regular:  output = cpu_count * ratio
  regular → hp:  output = ceil(cpu_count / ratio * 2) / 2  (nearest 0.5)
"""

import math

from app.config import settings
from app.errors import ValidationError


def _round_to_half(value: float) -> float:
    """Round up to nearest 0.5."""
    return math.ceil(value * 2) / 2


def convert_cpu(cpu_count: int, from_tier: str, to_tier: str) -> dict:
    if cpu_count <= 0:
        raise ValidationError("cpu_count must be greater than 0")
    if from_tier == to_tier:
        raise ValidationError("from_tier and to_tier must be different")

    ratio = settings.CPU_HP_TO_REGULAR_RATIO

    if from_tier == "high_performance" and to_tier == "regular":
        output = cpu_count * ratio
    elif from_tier == "regular" and to_tier == "high_performance":
        output = _round_to_half(cpu_count / ratio)
    else:
        raise ValidationError(
            f"Unsupported tier combination: {from_tier} → {to_tier}"
        )

    return {
        "input_cpu": cpu_count,
        "output_cpu": output,
        "from_tier": from_tier,
        "to_tier": to_tier,
        "ratio_used": ratio,
    }


def get_conversion_info() -> dict:
    ratio = settings.CPU_HP_TO_REGULAR_RATIO
    return {
        "ratio": ratio,
        "description": f"1 high_performance CPU = {ratio} regular CPUs",
    }
