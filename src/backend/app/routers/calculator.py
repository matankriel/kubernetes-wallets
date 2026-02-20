"""CPU tier calculator endpoints.

GET  /api/v1/calculator/cpu-conversion  — ratio info (no auth required)
POST /api/v1/calculator/convert          — convert cpu count between tiers (no auth required)
"""

from fastapi import APIRouter
from pydantic import BaseModel, field_validator

from app.services.calculator_service import convert_cpu, get_conversion_info

router = APIRouter(prefix="/api/v1/calculator", tags=["calculator"])


class ConvertRequest(BaseModel):
    cpu_count: int
    from_tier: str
    to_tier: str

    @field_validator("from_tier", "to_tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        allowed = {"regular", "high_performance"}
        if v not in allowed:
            msg = f"tier must be one of {allowed}"
            raise ValueError(msg)
        return v


class ConversionInfoResponse(BaseModel):
    ratio: float
    description: str


class ConvertResponse(BaseModel):
    input_cpu: int
    output_cpu: float
    from_tier: str
    to_tier: str
    ratio_used: float


@router.get("/cpu-conversion", response_model=ConversionInfoResponse)
async def cpu_conversion_info() -> ConversionInfoResponse:
    return ConversionInfoResponse(**get_conversion_info())


@router.post("/convert", response_model=ConvertResponse)
async def convert(body: ConvertRequest) -> ConvertResponse:
    result = convert_cpu(body.cpu_count, body.from_tier, body.to_tier)
    return ConvertResponse(**result)
