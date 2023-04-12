from typing import Tuple

from brother_ql.labels import FormFactor
from pydantic import BaseModel


TwoDimValue = Tuple[int, int]
"A two dimensional value. The first dimension corresponds to the width of the tape"


class LabelSpecs(BaseModel):
    """Describes one label type"""
    name: str
    identifier: str
    form_factor: FormFactor
    tape_size: TwoDimValue
    "if tape is of kind ENDLESS, value in the second dimension is 0"

    dots_total: TwoDimValue
    "'pixels' including printer margins"

    dots_printable: TwoDimValue
    "'pixels' in printable area. if tape is of kind ENDLESS, value in the second dimension is 0"

    is_default: bool
    "If true, this is the label defined as default"
