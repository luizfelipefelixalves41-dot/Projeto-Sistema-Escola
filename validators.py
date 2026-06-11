import re


def somente_digitos(valor):
    return re.sub(r"\D", "", valor or "")


def cpf_valido(cpf):
    digitos = somente_digitos(cpf)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False

    for tamanho in (9, 10):
        soma = sum(int(digitos[indice]) * (tamanho + 1 - indice) for indice in range(tamanho))
        verificador = (soma * 10) % 11
        if verificador == 10:
            verificador = 0
        if verificador != int(digitos[tamanho]):
            return False

    return True


def normalizar_cpf(cpf):
    digitos = somente_digitos(cpf)
    if len(digitos) != 11:
        return cpf.strip()
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def inteiro_positivo(valor):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return None
    return numero if numero > 0 else None


def pagina_atual(valor):
    try:
        pagina = int(valor)
    except (TypeError, ValueError):
        return 1
    return max(pagina, 1)
