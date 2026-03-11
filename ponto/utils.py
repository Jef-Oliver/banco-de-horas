def format_minutos_hhmm(minutos):
    """Converte minutos inteiros para formato HH:MM (ex: 65 -> 01:05, -60 -> -01:00)"""
    if minutos is None:
        return "00:00"
    
    abs_minutos = abs(minutos)
    horas = abs_minutos // 60
    mins = abs_minutos % 60
    
    sign = "-" if minutos < 0 else ""
    return f"{sign}{horas:02d}:{mins:02d}"

def hm_para_minutos(hhmm):
    """Converte string HH:MM para minutos inteiros"""
    if not hhmm or ":" not in hhmm:
        return 0
    try:
        partes = hhmm.split(":")
        horas = int(partes[0])
        mins = int(partes[1])
        if horas < 0:
            return horas * 60 - mins
        return horas * 60 + mins
    except (ValueError, IndexError):
        return 0
