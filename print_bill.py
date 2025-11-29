from datetime import datetime
from typing import Any, Dict, List, Optional
from win32 import win32print
from rest_framework.exceptions import APIException
from unidecode import unidecode
import os
from dotenv import load_dotenv

load_dotenv()

# dish_name da impressora (substitua com o dish_name da sua impressora ESC/P)
default_printer = os.getenv('BILL_PRINTER')

CUT = b"\x1B\x69"

class PrinterOfflineException(APIException):
    status_code = 503
    default_detail = "A impressora está offline ou não está acessível."
    default_code = "printer_offline"
    
def is_printer_offline_all():
    try:
        hPrinter = win32print.OpenPrinter(default_printer)
        # Nível 2 retorna um dicionário com informações detalhadas sobre a impressora
        printer_info = win32print.GetPrinter(hPrinter, 2)
        # print(printer_info)
        win32print.ClosePrinter(hPrinter)
        return False
    except:
        return True

def print_order_bill(order_data):
    """
    Imprime uma conta detalhada: cabeçalho e mensagens centralizadas,
    itens e totais alinhados à esquerda.
    """
    if is_printer_offline_all():
        raise PrinterOfflineException()

    try:
        payload = build_bill_payload(order_data)

        hPrinter = win32print.OpenPrinter(default_printer)
        win32print.StartDocPrinter(hPrinter, 1, (payload["title"], None, "RAW"))
        win32print.StartPagePrinter(hPrinter)

        logo_bytes = build_logo()
        if logo_bytes:
            win32print.WritePrinter(hPrinter, logo_bytes)

        win32print.WritePrinter(hPrinter, payload["content"])
        win32print.WritePrinter(hPrinter, CUT)

        win32print.EndPagePrinter(hPrinter)
        win32print.EndDocPrinter(hPrinter)
        win32print.ClosePrinter(hPrinter)

    except Exception as e:
        raise APIException(f"Erro durante a impressão: {str(e)}")


def build_bill_payload(order_data):
    order_id = order_data["id"]
    original_date_time = order_data["date_time"]
    date_object = datetime.fromisoformat(original_date_time[:-2] + "00")
    date_time = date_object.strftime("%d-%m-%Y %H:%M:%S")

    table_number = order_data["table_number"]
    order_dishes = order_data.get("order_dishes", [])
    waiter = order_data["waiter"]
    is_outside = order_data["is_outside"]

    subtotal = float(order_data.get("total", 0) or 0)
    service_fee = float(order_data.get("service", 0) or 0)
    amount_due = float(order_data.get("amount_to_pay", subtotal + service_fee) or 0)

    company_name = order_data.get("company_name", "")
    company_address = order_data.get("company_address", "")
    company_cnpj = order_data.get("company_cnpj", "")
    company_ie = order_data.get("company_ie", "")
    access_key = order_data.get("access_key", "")
    qr_number = order_data.get("qr_number", "")
    qr_url = order_data.get("qr_url", "https://sat.ef.sc.gov.br/nfce/consulta")
    nfce_number = order_data.get("nfce_number", "")
    nfce_series = order_data.get("nfce_series", "")
    protocol = order_data.get("protocol", "")
    protocol_datetime = order_data.get("protocol_datetime", "")
    total_taxes = order_data.get("total_taxes", "")
    md5_hash = order_data.get("md5", "")

    content = b""
    content += reset_and_center()
    content += text_small(company_name + "\\n")
    content += text_small(company_address + "\\n")
    content += text_small(f"CNPJ: {company_cnpj}  IE: {company_ie}\\n")
    content += text_small("Documento Auxiliar da Nota Fiscal de Consumidor Eletronica\\n\\n")

    content += text_medium(f"# Conta {order_id}\\n")
    content += text_small(f"Data: {date_time}\\n")
    content += text_small(f"Mesa: {'R' + str(table_number) if is_outside else table_number}\\n")
    content += text_small(f"Atendente: {waiter}\\n\\n")

    content += align_left()
    content += render_items(order_dishes)

    content += text_medium("--------------------\\n")
    content += text_medium(f"Valor total da conta: R$ {subtotal:0.2f}\\n")
    content += text_medium(f"Servico: R$ {service_fee:0.2f}\\n")
    content += text_big(f"Valor a Pagar: R$ {amount_due:0.2f}\\n")

    content += align_center()
    content += text_small("\\nConsulte pela chave de acesso em\\n")
    content += text_small(f"{qr_url}\\n")
    if access_key:
        content += text_small(f"{access_key}\\n")
    if qr_number:
        content += text_small(f"QR Code: {qr_number}\\n")
    content += text_small("CONSUMIDOR NAO IDENTIFICADO\\n\\n")

    content += text_small(
        f"NFC-e n {nfce_number} Serie {nfce_series} data emissao {date_time}\\n"
    )
    content += text_small(f"Protocolo de Autorizacao: {protocol}\\n")
    if protocol_datetime:
        content += text_small(f"Data Autorizacao {protocol_datetime}\\n")

    content += text_small("\\n[ QR CODE ]\\n")

    if total_taxes:
        content += text_small(
            f"Tributos Totais Incidentes (Lei Federal 12.741/2012): {total_taxes}\\n"
        )
    if md5_hash:
        content += text_small(f"MD5: {md5_hash}\\n")

    return {
        "title": f"conta_{order_id}_mesa_{table_number}",
        "content": content,
    }


def build_logo() -> Optional[bytes]:
    """
    Gera bytes ESC/POS de uma imagem (logo) se BILL_LOGO_PATH estiver definido.
    Redimensiona para largura máxima em pontos (default 384) e modo 1-bit.
    """
    logo_path = os.getenv("BILL_LOGO_PATH")
    if not logo_path:
        return None
    max_width = int(os.getenv("BILL_LOGO_MAX_WIDTH_DOTS", "384"))

    try:
        from PIL import Image
    except Exception:
        return None

    try:
        img = Image.open(logo_path)
        img = img.convert("L")
        # Reduzir à largura máxima mantendo proporção
        if img.width > max_width:
            ratio = max_width / float(img.width)
            img = img.resize((max_width, int(img.height * ratio)))
        # largura múltipla de 8 para ESC/POS
        width = (img.width + 7) // 8 * 8
        if width != img.width:
            img = img.resize((width, img.height))
        img = img.convert("1")  # binário

        row_bytes = width // 8
        xL = row_bytes % 256
        xH = row_bytes // 256
        yL = img.height % 256
        yH = img.height // 256

        # Comando raster bit image (GS v 0)
        header = b"\x1D\x76\x30\x00" + bytes([xL, xH, yL, yH])
        return header + img.tobytes()
    except Exception:
        return None


def render_items(order_dishes: List[Dict[str, Any]]) -> bytes:
    buffer = b""
    for order_dish in order_dishes:
        dish = order_dish.get("dish", {})
        dish_name = dish.get("dish_name", "")
        amount = order_dish.get("amount", 0)
        unit_price = order_dish.get("unit_price") or dish.get("price") or 0
        line_total = float(amount) * float(unit_price)
        left = f"{dish_name} / {amount} UN x R$ {float(unit_price):0.2f}"
        # Ensure separation; not perfect alignment but keeps total at line end
        buffer += text_medium(f"{left}    R$ {line_total:0.2f}\\n")
    return buffer


def reset_and_center():
    return b"\x1B\x40" + align_center()


def align_left():
    return b"\x1B\x61\x00"


def align_center():
    return b"\x1B\x61\x01"


def text_small(text):
    return align_current_size(b"\x1B\x21\x00", text)


def text_medium(text):
    return align_current_size(b"\x1B\x21\x20", text)


def text_big(text):
    return align_current_size(b"\x1B\x21\x30", text)


def align_current_size(size_cmd, text):
    return size_cmd + format_text(text, "").encode("utf-8")

# Exemplo de uso:
# texto_big = formatar_texto("Este é um texto de exemplo para testar a formatação.", 'big')
# texto_medium = formatar_texto("Este é um texto de exemplo para testar a formatação.", 'medium')
# texto_small = formatar_texto("Este é um texto de exemplo para testar a formatação.", 'small')

def format_text(text, other):
        return unidecode(text)
