from datetime import datetime
from typing import Any, Dict, List, Optional
from win32 import win32print
from rest_framework.exceptions import APIException
from unidecode import unidecode
import os
from dotenv import load_dotenv

load_dotenv()

default_printer = os.getenv('BILL_PRINTER')

CUT = b"\x1B\x69"  # corte total Epson ESC/POS
BEEP_TIMES = 1
BEEP_DURATION = 3


class PrinterOfflineException(APIException):
    status_code = 503
    default_detail = "A impressora está offline ou não está acessível."
    default_code = "printer_offline"


def is_printer_offline_all():
    try:
        hPrinter = win32print.OpenPrinter(default_printer)
        win32print.GetPrinter(hPrinter, 2)
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

    hPrinter = None
    doc_started = False
    page_started = False

    try:
        payload = build_bill_payload(order_data)

        hPrinter = win32print.OpenPrinter(default_printer)
        win32print.StartDocPrinter(hPrinter, 1, (payload["title"], None, "RAW"))
        doc_started = True
        win32print.StartPagePrinter(hPrinter)
        page_started = True

        # logo_bytes = build_logo()
        # if logo_bytes:
        #     win32print.WritePrinter(hPrinter, align_center())
        #     win32print.WritePrinter(hPrinter, logo_bytes)

        # win32print.WritePrinter(hPrinter, payload["content"])
        # win32print.WritePrinter(hPrinter, CUT)
        emitir_beep(hPrinter)

    except Exception as e:
        raise APIException(f"Erro durante a impressão: {str(e)}")
    finally:
        if page_started and hPrinter:
            try:
                win32print.EndPagePrinter(hPrinter)
            except Exception:
                pass
        if doc_started and hPrinter:
            try:
                win32print.EndDocPrinter(hPrinter)
            except Exception:
                pass
        if hPrinter:
            try:
                win32print.ClosePrinter(hPrinter)
            except Exception:
                pass


def build_bill_payload(order_data):
    company_name = order_data.get("company_name", "")
    company_address = order_data.get("company_address", "")
    company_cnpj = order_data.get("company_cnpj", "")
    company_ie = order_data.get("company_ie", "")
    order_dishes = order_data.get("order_dishes", [])
    subtotal = float(order_data.get("subtotal", 0) or 0)
    service_fee = float(order_data.get("service_fee", 0) or 0)
    final_value = float(order_data.get("final_value", 0) or 0)
    access_key_url = order_data.get("access_key_url", "")
    access_key = order_data.get("access_key", "")
    qr_url = order_data.get("qr_url", "")
    nfce_number = order_data.get("nfce_number", "")
    nfce_series = order_data.get("nfce_series", "")
    emission_datetime = order_data.get("emission_datetime", "")
    authorization_protocol = order_data.get("authorization_protocol", "")
    authorization_datetime = order_data.get("authorization_datetime", "")

    content = b""

    # resetar impressora e centralizar
    content += reset_and_center()
    content += text_smallest(company_name + "\n")
    content += text_smallest(company_address + "\n")
    content += text_smallest(f"CNPJ: {company_cnpj}  IE: {company_ie}\n")
    content += text_smallest("Documento Auxiliar da Nota Fiscal de Consumidor Eletronica\n\n")

    content += b"\n"
    
    content += align_left()
    content += render_item_line(
        "Item  |  Quantidade  |  Valor Unitario",
        "Soma",
        formatter=text_smallest,
    )
    content += render_items(order_dishes)
    
    content += b"\n"
    content += b"\n"
    
    content += render_item_line(
        f"Subtotal: R$ {subtotal:0.2f}",
        f"R$ {subtotal:0.2f}",
        formatter=text_medium,
    )
    content += render_item_line(
        f"Serviço: R$ {service_fee:0.2f}",
        f"R$ {service_fee:0.2f}",
        formatter=text_medium,
    )
    content += render_item_line(
        f"Valor total: R$ {final_value:0.2f}",
        f"R$ {final_value:0.2f}",
        formatter=text_medium,
    )

    content += align_center()
    content += text_smallest("\nConsulte pela chave de acesso em\n")
    content += text_smallest(f"{access_key_url}\n")
    content += text_smallest(f"{access_key}\n")
    content += text_smallest("CONSUMIDOR NAO IDENTIFICADO\n\n")

    content += text_smallest(
        f"NFC-e n {nfce_number} Serie {nfce_series} | Data Emissao: {emission_datetime}\n"
    )
    content += text_smallest(f"Protocolo de Autorizacao: {authorization_protocol}\n")
    content += text_smallest(f"Data Autorizacao: {authorization_datetime}\n")

    content += align_center()

    # Gera QR CODE a partir da chave de acesso se existir
    content += escpos_qr(qr_url)
    
    # umas linhas em branco no final antes do corte
    content += b"\n\n\n\n"

    order_id = order_data.get("id", "sem_id")
    table_number = order_data.get("table_number", "sem_mesa")

    return {
        "title": f"conta_{order_id}_mesa_{table_number}",
        "content": content,
    }


def build_logo() -> Optional[bytes]:
    """
    Gera bytes ESC/POS do logo e registra logs de diagnóstico.
    """
    logo_path = os.getenv("BILL_LOGO_PATH")

    print("\n[LOGO] Iniciando carregamento do logo...")

    if not logo_path:
        print("[LOGO] Variável BILL_LOGO_PATH não definida.")
        return None

    print(f"[LOGO] Caminho informado: {logo_path}")

    if not os.path.exists(logo_path):
        print("[LOGO] ARQUIVO NÃO ENCONTRADO! Verifique o caminho.")
        return None

    max_width = int(os.getenv("BILL_LOGO_MAX_WIDTH_DOTS", "384"))
    print(f"[LOGO] Largura máxima definida: {max_width} dots")

    try:
        from PIL import Image
    except Exception:
        print("[LOGO] ERRO: Biblioteca Pillow não instalada.")
        return None

    try:
        img = Image.open(logo_path)
        print(f"[LOGO] Imagem carregada com sucesso: {img.size} px")

        # Converter para escala cinza
        img = img.convert("L")

        # Redimensionar
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(img.height * ratio)
            print(f"[LOGO] Redimensionando imagem para: {max_width}x{new_height}")
            img = img.resize((max_width, new_height))

        # Ajustar largura para múltiplo de 8
        width = (img.width + 7) // 8 * 8
        if width != img.width:
            print(f"[LOGO] Ajustando largura para múltiplo de 8: {width}")
            img = img.resize((width, int(img.height)))

        # Converter para 1-bit
        img = img.convert("1")
        print(f"[LOGO] Dimensão final do logo: {img.size}")

        # ESC/POS: raster bit image (GS v 0)
        row_bytes = width // 8
        xL = row_bytes % 256
        xH = row_bytes // 256
        yL = img.height % 256
        yH = img.height // 256

        print("[LOGO] Gerando header ESC/POS raster...")
        header = b"\x1D\x76\x30\x00" + bytes([xL, xH, yL, yH])

        data = img.tobytes()
        print(f"[LOGO] Bytes de imagem gerados: {len(data)} bytes")

        print("[LOGO] LOGO preparado com sucesso!\n")
        return header + data + b"\n"  # ← importante para TM-T20X

    except Exception as e:
        print(f"[LOGO] ERRO AO PROCESSAR IMAGEM: {e}\n")
        return None


def escpos_qr(data: str) -> bytes:
    """
    Gera um QR Code real usando comandos ESC/POS nativos Epson.
    Compatível com TM-T20X.
    """

    qr_bytes = data.encode("utf-8")
    length = len(qr_bytes)

    cmd = b""

    # Seleciona modelo
    cmd += b"\x1D\x28\x6B\x04\x00\x31\x41\x32\x00"

    # Tamanho do módulo (1 a 16)
    cmd += b"\x1D\x28\x6B\x03\x00\x31\x43\x06"  # módulo = 6

    # Nível de correção (48=L, 49=M, 50=Q, 51=H)
    cmd += b"\x1D\x28\x6B\x03\x00\x31\x45\x31"  # M

    # Armazena dados
    pL = (length + 3) % 256
    pH = (length + 3) // 256
    cmd += bytes([0x1D, 0x28, 0x6B, pL, pH, 0x31, 0x50, 0x30]) + qr_bytes

    # Imprime o QR
    cmd += b"\x1D\x28\x6B\x03\x00\x31\x51\x30"

    return cmd + b"\n"


def render_items(order_dishes: List[Dict[str, Any]]) -> bytes:
    buffer = b""
    for order_dish in order_dishes:
        dish = order_dish.get("dish", {})
        dish_name = dish.get("dish_name", "")
        amount = order_dish.get("amount", 0)
        unit_price = order_dish.get("unit_price") or dish.get("price") or 0
        line_total = float(amount) * float(unit_price)

        left = f"{dish_name} - {amount} UN x R$ {float(unit_price):0.2f}"
        right = f"R$ {line_total:0.2f}"
        buffer += render_item_line(left, right, formatter=text_small)

    return buffer


def reset_and_center():
    return b"\x1B\x40" + align_center()  # ESC @ (reset) + centralizar


def align_left():
    return b"\x1B\x61\x00"  # ESC a 0


def align_center():
    return b"\x1B\x61\x01"  # ESC a 1


def text_smallest(text: str) -> bytes:
    return (
        b"\x1B\x21\x00" +   # reset tamanho
        b"\x1B\x4D\x01" +   # Font B (menor)
        format_text(text, "").encode("utf-8")
    )

def text_small(text: str) -> bytes:
    return (
        b"\x1B\x21\x00" +   # tamanho normal
        b"\x1B\x4D\x00" +   # Font A
        format_text(text, "").encode("utf-8")
    )

def text_medium(text: str) -> bytes:
    return (
        b"\x1B\x21\x20" +   # altura dobrada
        b"\x1B\x4D\x00" +   # Font A
        format_text(text, "").encode("utf-8")
    )
    
def text_big(text: str) -> bytes:
    return (
        b"\x1B\x21\x30" +   # altura+largo dobrado
        b"\x1B\x4D\x00" +   # Font A
        format_text(text, "").encode("utf-8")
    )

def align_current_size(size_cmd: bytes, text: str) -> bytes:
    """
    Aplica o comando de tamanho e retorna o texto formatado com \n corretos.
    """
    return size_cmd + format_text(text, "").encode("utf-8")


def format_text(text: str, other: str) -> str:
    # mantém quebras de linha e remove acentos
    # (unidecode não remove '\n', então é safe)
    return unidecode(text)

def emitir_beep(hPrinter, times=BEEP_TIMES, duration=BEEP_DURATION):
    """
    Dispara o comando de buzzer via ESC/POS usando ESC ( A.
    times e duration devem estar entre 1 e 9.
    """
    # garante intervalo válido
    times = max(1, min(9, int(times)))
    duration = max(1, min(9, int(duration)))

    # Comando ESC/POS para beep:
    # 1B 28 41 03 00 30 <times> <duration>
    comando = b'\x1B\x28\x41\x03\x00\x30' + bytes([times, duration])

    # envia "raw" para impressora
    win32print.WritePrinter(hPrinter, comando)



def render_item_line(
    left: str,
    right: str,
    width: int = 48,
    formatter=text_small,
) -> bytes:
    """
    Monta uma linha com o texto da esquerda e o valor à direita.
    Exemplo:
    "Coca-Cola 2un x 5,00              R$ 10,00"
    """
    left = format_text(left, "")
    right = format_text(right, "")

    # calcula quantidade de espaços necessários
    spaces = width - len(left) - len(right)

    if spaces < 1:
        spaces = 1  # evita colar textos quando ultrapassa

    line = left + (" " * spaces) + right + "\n"
    return formatter(line)
