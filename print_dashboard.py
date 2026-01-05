import os
from datetime import datetime

from dotenv import load_dotenv
from rest_framework.exceptions import APIException
from unidecode import unidecode
from win32 import win32print

load_dotenv()

REPORT_PRINTER = os.getenv("REPORT_PRINTER") or os.getenv("BILL_PRINTER")
CUT = b"\x1B\x69"
WEEKDAY_LABELS = [
    "Segunda-feira",
    "Terca-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sabado",
    "Domingo",
]


class PrinterOfflineException(APIException):
    status_code = 503
    default_detail = "A impressora está offline ou não está acessível."
    default_code = "printer_offline"


class PrinterNotConfiguredException(APIException):
    status_code = 500
    default_detail = (
        "Configure a variável REPORT_PRINTER ou BILL_PRINTER para imprimir o relatório."
    )
    default_code = "printer_not_configured"


def _require_printer() -> str:
    if not REPORT_PRINTER:
        raise PrinterNotConfiguredException()
    return REPORT_PRINTER


def is_printer_offline() -> bool:
    try:
        printer_name = _require_printer()
        handle = win32print.OpenPrinter(printer_name)
        win32print.GetPrinter(handle, 2)
        win32print.ClosePrinter(handle)
        return False
    except PrinterNotConfiguredException:
        raise
    except Exception:
        return True


def print_dashboard_summary(report_data):
    printer_name = _require_printer()
    if is_printer_offline():
        raise PrinterOfflineException()

    hPrinter = None
    doc_started = False
    page_started = False

    try:
        payload = build_summary_payload(report_data)
        hPrinter = win32print.OpenPrinter(printer_name)
        win32print.StartDocPrinter(
            hPrinter, 1, ("relatorio_dashboard", None, "RAW")
        )
        doc_started = True
        win32print.StartPagePrinter(hPrinter)
        page_started = True

        win32print.WritePrinter(hPrinter, payload)
        win32print.WritePrinter(hPrinter, CUT)
    except Exception as exc:
        raise APIException(f"Erro durante a impressão: {exc}")
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


def build_summary_payload(report_data) -> bytes:
    start_label = format_date_label(report_data.get("start_date"))
    end_label = format_date_label(
        report_data.get("end_date") or report_data.get("start_date")
    )
    total_additions = float(report_data.get("total_additions") or 0)
    printed_at = format_datetime_label(report_data.get("printed_at"))
    printed_by = str(report_data.get("printed_by") or "").strip()
    daily_entries = normalize_daily_breakdown(report_data)

    if not end_label:
        end_label = start_label

    if start_label == end_label:
        period_line = f"Periodo: {start_label or '--'}"
    else:
        period_line = f"Periodo: {start_label} a {end_label}"

    content = b""
    content += reset_printer()
    content += align_center()
    content += text_big("Relatório de serviço\n")
    content += text_small("\n")
    content += align_left()
    content += text_small(period_line + "\n")
    if printed_at:
        content += text_small(f"Gerado em: {printed_at}\n")
    if printed_by:
        content += text_small(f"Por: {printed_by}\n")
    content += text_small("\n")

    if not daily_entries:
        content += text_medium("Sem movimentacao no periodo.\n")
        content += text_small("\n")
    else:
        for entry in daily_entries:
            weekday_label, day_month_label = format_weekday_day_label(entry.get("date"))
            content += text_medium(
                f"{weekday_label} {day_month_label}: R$ {entry['total_additions']:0.2f}\n"
            )
            content += text_small(f"Mesas atendidas: {entry['total_tables']}\n\n")

    content += text_medium(f"Total dos 10% no periodo: R$ {total_additions:0.2f}\n")
    content += b"\n\n\n\n"
    return content


def format_weekday_day_label(value):
    parsed = parse_iso_date(value)
    if not parsed:
        return "--", "--/--"
    weekday_label = WEEKDAY_LABELS[parsed.weekday()]
    day_month_label = parsed.strftime("%d/%m")
    return weekday_label, day_month_label


def parse_iso_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def normalize_daily_breakdown(report_data):
    breakdown = report_data.get("daily_breakdown")
    if not isinstance(breakdown, list):
        return []

    normalized = []
    for entry in breakdown:
        if not isinstance(entry, dict):
            continue
        normalized.append(
            {
                "date": entry.get("date"),
                "total_additions": float(entry.get("total_additions") or 0),
                "total_tables": int(entry.get("total_tables") or 0),
            }
        )

    normalized.sort(key=lambda item: item.get("date") or "")
    return normalized


def format_date_label(value):
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return str(value)
    return parsed.strftime("%d/%m/%Y")


def format_datetime_label(value):
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return str(value)
    return parsed.strftime("%d/%m/%Y %H:%M")


def reset_printer():
    return b"\x1B\x40"


def align_left():
    return b"\x1B\x61\x00"


def align_center():
    return b"\x1B\x61\x01"


def text_small(text: str) -> bytes:
    return b"\x1B\x21\x00" + format_text(text).encode("utf-8")


def text_medium(text: str) -> bytes:
    return b"\x1B\x21\x20" + format_text(text).encode("utf-8")


def text_big(text: str) -> bytes:
    return b"\x1B\x21\x30" + format_text(text).encode("utf-8")


def format_text(text: str) -> str:
    return unidecode(text or "")
