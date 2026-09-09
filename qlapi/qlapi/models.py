from typing import Optional, Tuple

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


class PrinterHealth(BaseModel):
    """Reachability status of one configured printer"""
    name: str
    model: str
    backend: str
    available: bool
    error: Optional[str]
    "reason the printer is unreachable, if any"


class JobAccepted(BaseModel):
    """Returned when a print job has been queued"""
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    """Status of a previously submitted print job"""
    job_id: str
    status: str
    error: Optional[str]
    "reason the job failed, if any"
