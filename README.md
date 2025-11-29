# Marinheiros Printer API

API simples para despachar impressao de comandas usando os fluxos existentes (`print_bar.py` e `print_kitchen.py`).

## Rodando local
1. Crie/ajuste variaveis de ambiente: `BAR_PRINTER` (copa/bar) e `DEFAULT_PRINTER` (cozinha).
2. Instale deps base: `pip install fastapi uvicorn pydantic djangorestframework python-dotenv pywin32 unidecode`.
3. Suba o servidor: `uvicorn main:app --host 0.0.0.0 --port 8000`.

## Endpoints
- `GET /health` — verifica se a API esta online.
- `POST /print-bar` — imprime apenas itens do departamento `copa` na impressora da copa/bar.
- `POST /print-kitchen` — imprime apenas itens do departamento `cozinha` na impressora da cozinha.

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

## Colecao Postman (Marinheiros)
- Arquivo: `marinheiros-printer.postman_collection.json`.
- Configure a variavel `base_url` (default: `http://localhost:8000`).
- Requests incluidos:
  - **Health** (`GET {{base_url}}/health`)
  - **Print Bar** (`POST {{base_url}}/print-bar`) com body de exemplo do Order.
  - **Print Kitchen** (`POST {{base_url}}/print-kitchen`) com body de exemplo do Order.

Importe o arquivo no Postman (File > Import) e selecione a colecao para testar os endpoints.
