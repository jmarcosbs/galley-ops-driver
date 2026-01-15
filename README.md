# Galley Ops Driver API

API simples para despachar impressao de comandas usando os fluxos existentes (`print_bar.py` e `print_kitchen.py`).

## Rodando local
1. Crie/ajuste variaveis de ambiente: `BAR_PRINTER` (copa/bar), `DEFAULT_PRINTER` (cozinha), `BILL_PRINTER` (conta), `BILL_LOGO_PATH` (caminho para a imagem do logo, opcional) e `BILL_LOGO_MAX_WIDTH_DOTS` (largura max em pontos, default 384).
2. Instale deps base: `pip install fastapi uvicorn pydantic djangorestframework python-dotenv pywin32 unidecode Pillow`.
3. Suba o servidor: `uvicorn main:app --host 0.0.0.0 --port 8000`.

## Endpoints
- `GET /health` — verifica se a API esta online.
- `POST /print-bar` — imprime apenas itens do departamento `copa` na impressora da copa/bar.
- `POST /print-kitchen` — imprime apenas itens do departamento `cozinha` na impressora da cozinha.
- `POST /print-bill` — imprime a conta final com itens, servico e total a pagar.

### Corpo esperado (Order)
```json
{
  "id": 1,
  "date_time": "2024-06-14T18:30:00.000Z",
  "table_number": 12,
  "order_dishes": [
    {
      "dish": {"dish_name": "Suco de Laranja", "department": "copa"},
      "amount": 1,
      "dish_note": "sem acucar"
    },
    {
      "dish": {"dish_name": "Pizza Margherita", "department": "cozinha"},
      "amount": 1,
      "dish_note": null
    }
  ],
  "order_note": "",
  "waiter": "Joao",
  "is_outside": false
}
```

### Corpo esperado (Bill)
```json
{
  "id": 3,
  "date_time": "2024-06-14T20:00:00.000Z",
  "table_number": 8,
  "order_dishes": [
    {
      "dish": {"dish_name": "Cerveja", "department": "copa", "price": 9.5},
      "amount": 2,
      "dish_note": null,
      "unit_price": 9.5
    },
    {
      "dish": {"dish_name": "Hamburguer", "department": "cozinha", "price": 28},
      "amount": 1,
      "dish_note": "bem passado",
      "unit_price": 28
    }
  ],
  "order_note": "",
  "waiter": "Joao",
  "is_outside": false,
  "total": 47,
  "service": 4.7,
  "amount_to_pay": 51.7,
  "company_name": "Restaurante Exemplo LTDA",
  "company_address": "Rua das Flores, 123 - Centro - Cidade/UF",
  "company_cnpj": "00.000.000/0001-00",
  "company_ie": "123456789",
  "access_key": "00000000000000000000000000000000000000000000",
  "qr_number": "1234567890",
  "qr_url": "https://sat.ef.sc.gov.br/nfce/consulta",
  "nfce_number": "118",
  "nfce_series": "1",
  "protocol": "242251682270691",
  "protocol_datetime": "2024-06-14 20:00:00",
  "total_taxes": "R$ 3,50",
  "md5": "abc123..."
}
```

## Colecao Postman
- Arquivo: `printer.postman_collection.json` (em `docs/`).
- Configure a variavel `base_url` (default: `http://localhost:8000`).
- Requests incluidos:
  - **Health** (`GET {{base_url}}/health`)
  - **Print Bar** (`POST {{base_url}}/print-bar`) com body de exemplo do Order.
  - **Print Kitchen** (`POST {{base_url}}/print-kitchen`) com body de exemplo do Order.
  - **Print Bill** (`POST {{base_url}}/print-bill`) com body de exemplo do Bill.

Importe o arquivo no Postman (File > Import) e selecione a colecao para testar os endpoints.
