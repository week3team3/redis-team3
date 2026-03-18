from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class SeatStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    HELD = "HELD"
    SOLD = "SOLD"


class CreateEventRequest(BaseModel):
    eventId: str = Field(min_length=1)
    title: str = Field(min_length=1)
    seats: list[str] = Field(min_length=1)

    @field_validator("seats")
    @classmethod
    def validate_seats(cls, seats: list[str]) -> list[str]:
        cleaned = [seat.strip() for seat in seats]
        if any(not seat for seat in cleaned):
            raise ValueError("seat IDs must not be blank")
        return cleaned


class UserActionRequest(BaseModel):
    userId: str = Field(min_length=1)

    @field_validator("userId")
    @classmethod
    def validate_user_id(cls, user_id: str) -> str:
        user_id = user_id.strip()
        if not user_id:
            raise ValueError("userId must not be blank")
        return user_id


class CreateEventResponse(BaseModel):
    success: bool = True
    eventId: str


class SeatView(BaseModel):
    seatId: str
    status: SeatStatus
    userId: str | None = None
    ttl: int | None = None


class SeatActionResponse(BaseModel):
    success: bool = True
    seatId: str
    status: SeatStatus
    ttl: int | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    reason: str


class EventSeatsResponse(BaseModel):
    eventId: str
    seats: list[SeatView]


class EventStatusResponse(BaseModel):
    eventId: str
    available: int
    held: int
    sold: int
