from datetime import datetime
from typing import Any, Optional, Tuple

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


class TemplateMeta(BaseModel):
    """Metadata for a stored label-editor template (no canvas payload)."""
    id: str
    name: str
    label_identifier: str
    created_at: datetime
    updated_at: datetime


class Template(TemplateMeta):
    """A full stored template, including the Fabric.js canvas JSON."""
    canvas: Any


class TemplateSave(BaseModel):
    """Request body for creating/updating a template."""
    name: str
    label_identifier: str
    canvas: Any

