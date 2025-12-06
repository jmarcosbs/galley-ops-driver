from datetime import datetime
from win32 import win32print
from rest_framework.exceptions import APIException
from unidecode import unidecode
import os
from dotenv import load_dotenv

load_dotenv()

# dish_name da impressora (substitua com o dish_name da sua impressora ESC/P)
default_printer = os.getenv('KITCHEN_PRINTER')

class PrinterOfflineException(APIException):
    status_code = 503
    default_detail = "A impressora está offline ou não está acessível."
    default_code = "printer_offline"
    
def is_printer_offline_kitchen():
    try:
        hPrinter = win32print.OpenPrinter(default_printer)
        # Nível 2 retorna um dicionário com informações detalhadas sobre a impressora
        printer_info = win32print.GetPrinter(hPrinter, 2)
        # print(printer_info)
        win32print.ClosePrinter(hPrinter)
        return False
    except:
        return True

def print_order_kitchen(order_data):
    if is_printer_offline_kitchen():
        raise PrinterOfflineException()

    hPrinter = None
    doc_started = False
    page_started = False

    try:
        order_id = order_data['id']
        original_date_time = order_data['date_time']
        date_object = datetime.fromisoformat(original_date_time[:-2] + "00")
        date_time = date_object.strftime("%d-%m-%Y %H:%M:%S")

        table_number = order_data['table_number']
        order_dishes = order_data['order_dishes']
        order_note = order_data['order_note']
        waiter = order_data['waiter']
        is_outside = order_data['is_outside']

        hPrinter = win32print.OpenPrinter(default_printer)
        win32print.StartDocPrinter(
            hPrinter, 1, (f'pedido_{order_id}_mesa_{table_number}', None, "RAW")
        )
        doc_started = True
        win32print.StartPagePrinter(hPrinter)
        page_started = True

        hasKitchenOrder = any(
            order_dish.get('dish', {}).get('department') == 'kitchen'
            for order_dish in order_dishes
        )

        if hasKitchenOrder:
            win32print.WritePrinter(
                hPrinter, cabecalho_pedido(order_id, date_time, waiter, "Cozinha")
            )
            imprimir_cozinha(hPrinter, order_dishes)
            win32print.WritePrinter(
                hPrinter, rodape_pedido(order_note, table_number, is_outside)
            )

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

def cabecalho_pedido(order_id, data_time, waiter, titulo):
    comandos = (
        b'\x1B\x40'  # Resetar a impressora (ESC @)
        b'\x1B\x61\x01'  # Centralizar texto (ESC a 1)
        b'\x1B\x21\x20'  # Fonte média
        +
        format_text(f'#{titulo} {order_id}\n', 'medium').encode('utf-8')
        +
        b'\x1B\x61\x00'  # Alinhar à esquerda (ESC a 0)
        b'\x1B\x21\x00'  # Fonte pequena (ESC ! 0)
        +
        format_text(f'Data: {data_time}\n', 'small').encode('utf-8')
        +
        format_text(f'Atendente: {waiter}\n\n\n', 'small').encode('utf-8')
    )
    return comandos

def dishes_pedido(dish_name, amount, dish_note):
    comandos = (
        b'\x1B\x21\x30'  # Fonte muito grande (ESC ! 48)
        b'\x1B\x45\x01'  # Ativar negrito (ESC E 1)
        +
        format_text(f" {'Meio' if amount == 0.5 else str(int(amount)) + ' e meio' if amount > 0.5 and amount % 1 != 0 else int(amount)} - {dish_name}\n\n", 'big').encode('utf-8')

        +
        b'\x1B\x45\x00'  # Desativar negrito (ESC E 0)
        b'\x1B\x21\x20'  # Fonte média
        b'\x1B\x61\x01'  # Centralizar texto (ESC a 1)
        +
        format_text(f'{dish_note + '\n\n' if dish_note != None else ''}', 'medium').encode('utf-8')
    )
    return comandos

def rodape_pedido(order_note, table_number, is_outside):
    comandos = (
        b'\x1B\x61\x01'  # Centralizar texto (ESC a 1)
        +
        format_text(f'====\n\n{order_note + '\n\n' if order_note != '' else '\n'}', 'medium').encode('utf-8')
        +
        b'\x1B\x45\x01'  # Ativar negrito (ESC E 1)
        b'\x1B\x2D\x01'  # Ativa sublinhado
        b'\x1B\x21\x30'  # Fonte muito grande (ESC ! 48)
        +
        format_text(f"* Mesa {'R' + str(table_number) if is_outside else str(table_number)} *\n\n\n", 'big').encode('utf-8')
        +
        b'\x1B\x2D\x00'  # Desativa sublinhado
        b'\x1B\x45\x00'  # Desativar negrito (ESC E 0)
        b'\x1B\x61\x00'  # Alinhar à esquerda (ESC a 0)
        +
        format_text(f'\n----------------\n\n\n', 'medium').encode('utf-8')
    )
    return comandos


def imprimir_copa(hPrinter, order_dishes):
    for order_dish in order_dishes:
        dish = order_dish['dish']
        amount = order_dish['amount']
        dish_note = order_dish['dish_note']
        dish_name = dish['dish_name']
        win32print.WritePrinter(hPrinter, dishes_pedido(dish_name, amount, dish_note))

def imprimir_cozinha(hPrinter, order_dishes):
    for order_dish in order_dishes:
        dish = order_dish['dish']
        amount = order_dish['amount']
        dish_note = order_dish['dish_note']
        if dish['department'] == 'kitchen':
            # Enviar o comando para cada dish da cozinha
            dish_name = dish['dish_name']
            win32print.WritePrinter(hPrinter, dishes_pedido(dish_name, amount, dish_note))

# Exemplo de uso:
# texto_big = formatar_texto("Este é um texto de exemplo para testar a formatação.", 'big')
# texto_medium = formatar_texto("Este é um texto de exemplo para testar a formatação.", 'medium')
# texto_small = formatar_texto("Este é um texto de exemplo para testar a formatação.", 'small')

def format_text(text, other):
        return unidecode(text)
