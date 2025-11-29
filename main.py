from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from rest_framework.exceptions import APIException

import print_bar
import print_kitchen


class Dish(BaseModel):
    dish_name: str = Field(..., description="Dish name")
    department: str = Field(..., description="Department handling the item, e.g. cozinha")


class OrderDish(BaseModel):
    dish: Dish
    amount: float = Field(..., ge=0.0, description="Quantity of the dish")
    dish_note: Optional[str] = Field(default=None, description="Optional note for the dish")


class Order(BaseModel):
    id: int
    date_time: str = Field(..., description="ISO 8601 timestamp, e.g. 2024-06-14T18:30:00.000Z")
    table_number: int
    order_dishes: List[OrderDish]
    order_note: str = ""
    waiter: str
    is_outside: bool = False


app = FastAPI(title="Printer API", version="1.0.0")


def _handle_print_error(exc: Exception) -> None:
    if isinstance(exc, APIException):
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        raise HTTPException(status_code=status_code, detail=detail)
    raise HTTPException(status_code=500, detail=str(exc))


@app.post("/print-bar", status_code=202)
async def print_bar_endpoint(order: Order):
    try:
        print_bar.print_order_all(order.model_dump())
    except Exception as exc:
        _handle_print_error(exc)
    return {"message": "Sent to bar printer"}


@app.post("/print-kitchen", status_code=202)
async def print_kitchen_endpoint(order: Order):
    try:
        print_kitchen.print_order_kitchen(order.model_dump())
    except Exception as exc:
        _handle_print_error(exc)
    return {"message": "Sent to kitchen printer"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}
