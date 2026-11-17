from datetime import datetime


def discover_windows_printers():
    """Return locally installed Windows printers when pywin32 is available."""
    try:
        import win32print
    except ImportError:
        return []

    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    rows = []
    for printer in win32print.EnumPrinters(flags):
        name = printer[2]
        handle = None
        status = 'Online'
        try:
            handle = win32print.OpenPrinter(name)
            info = win32print.GetPrinter(handle, 2)
            if info['Status']:
                status = 'Attention'
        except win32print.error:
            status = 'Offline'
        finally:
            if handle:
                win32print.ClosePrinter(handle)
        rows.append({'name': name, 'status': status, 'last_seen': datetime.now()})
    return rows
