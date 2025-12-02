from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from rest_framework.exceptions import APIException

import print_bar
import print_kitchen
import print_bill


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
    order_note: Optional[str] = ""
    waiter: str
    is_outside: Optional[bool] = False


class BillDish(OrderDish):
    unit_price: float = Field(..., ge=0.0, description="Unit price of the dish")


class BillOrder(Order):
    order_dishes: List[BillDish]
    total: float = Field(..., ge=0.0, description="Subtotal do pedido")
    service: float = Field(0.0, ge=0.0, description="Valor do servico")
    amount_to_pay: float = Field(..., ge=0.0, description="Total a pagar")
    company_name: str = Field("", description="Razao social")
    company_address: str = Field("", description="Endereco completo")
    company_cnpj: str = Field("", description="CNPJ")
    company_ie: str = Field("", description="Inscricao estadual")
    access_key: str = Field("", description="Chave de acesso NFC-e")
    qr_number: str = Field("", description="Numero do QR code")
    qr_url: str = Field("https://sat.ef.sc.gov.br/nfce/consulta", description="URL de consulta NFC-e")
    nfce_number: str = Field("", description="Numero da NFC-e")
    nfce_series: str = Field("", description="Serie da NFC-e")
    protocol: str = Field("", description="Protocolo de autorizacao")
    protocol_datetime: str = Field("", description="Data/hora autorizacao")
    total_taxes: str = Field("", description="Total de tributos")
    md5: str = Field("", description="Hash MD5")


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
        print_bar.print_order_bar(order.model_dump())
    except Exception as exc:
        _handle_print_error(exc)
    return {"message": "Sent to bar printer"}


@app.post("/print-kitchen", status_code=202)
async def print_kitchen_endpoint(order: Order):
    try:
        # Printa o body
        print("📥 Recebido em /print-kitchen:")
        print(order.model_dump())
        print_kitchen.print_order_kitchen(order.model_dump())
    except Exception as exc:
        _handle_print_error(exc)
    return {"message": "Sent to kitchen printer"}


@app.post("/print-bill", status_code=202)
async def print_bill_endpoint(order: BillOrder):
    try:
        print_bill.print_order_bill(order.model_dump())
    except Exception as exc:
        _handle_print_error(exc)
    return {"message": "Bill sent to bill printer"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}
