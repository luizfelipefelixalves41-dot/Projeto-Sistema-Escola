import json
from datetime import datetime


def gerar_relatorio_json(dados, caminho=None):
    conteudo = json.dumps(dados, ensure_ascii=False, indent=2)
    if caminho:
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(conteudo)
    return conteudo


def gerar_relatorio_pdf(dados, caminho=None):
    linhas = _montar_linhas_relatorio(dados)
    conteudo = _criar_pdf_texto(linhas)
    if caminho:
        with open(caminho, "wb") as arquivo:
            arquivo.write(conteudo)
    return conteudo


def _montar_linhas_relatorio(dados):
    linhas = [
        "Relatorio do Sistema Academico",
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "ALUNOS",
    ]

    for aluno in dados.get("alunos", []):
        linhas.append(
            f"- {aluno.get('nome')} | CPF: {aluno.get('cpf')} | "
            f"Matricula: {aluno.get('matricula')} | Curso: {aluno.get('curso')}"
        )

    linhas.extend(["", "PROFESSORES"])
    for professor in dados.get("professores", []):
        linhas.append(
            f"- {professor.get('nome')} | CPF: {professor.get('cpf')} | "
            f"Registro: {professor.get('registro')} | Area: {professor.get('area')}"
        )

    linhas.extend(["", "DISCIPLINAS"])
    for disciplina in dados.get("disciplinas", []):
        linhas.append(
            f"- {disciplina.get('nome')} | Codigo: {disciplina.get('codigo')} | "
            f"Carga: {disciplina.get('carga_horaria')}h | "
            f"Professor: {disciplina.get('professor') or 'Sem professor'}"
        )

    linhas.extend(["", "MATRICULAS"])
    for matricula in dados.get("matriculas", []):
        status = matricula.get("status", "ativa")
        linhas.append(
            f"- {matricula.get('aluno')} em {matricula.get('disciplina')} "
            f"({matricula.get('codigo')}) | Status: {status}"
        )

    return linhas


def _criar_pdf_texto(linhas):
    paginas = _quebrar_paginas(linhas, linhas_por_pagina=42)
    objetos = []

    objetos.append("<< /Type /Catalog /Pages 2 0 R >>")
    page_refs = " ".join(f"{3 + index * 2} 0 R" for index in range(len(paginas)))
    objetos.append(f"<< /Type /Pages /Kids [{page_refs}] /Count {len(paginas)} >>")

    for index, pagina in enumerate(paginas):
        page_obj = 3 + index * 2
        content_obj = page_obj + 1
        stream = _montar_stream_pagina(pagina)
        objetos.append(
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> "
            f"/Contents {content_obj} 0 R >>"
        )
        objetos.append(
            f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream"
        )

    partes = ["%PDF-1.4\n"]
    offsets = [0]
    for numero, objeto in enumerate(objetos, start=1):
        offsets.append(sum(len(parte.encode("latin-1")) for parte in partes))
        partes.append(f"{numero} 0 obj\n{objeto}\nendobj\n")

    xref_offset = sum(len(parte.encode("latin-1")) for parte in partes)
    partes.append(f"xref\n0 {len(objetos) + 1}\n")
    partes.append("0000000000 65535 f \n")
    for offset in offsets[1:]:
        partes.append(f"{offset:010d} 00000 n \n")
    partes.append(
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF"
    )

    return "".join(partes).encode("latin-1")


def _quebrar_paginas(linhas, linhas_por_pagina):
    if not linhas:
        return [["Sem dados."]]
    return [
        linhas[indice : indice + linhas_por_pagina]
        for indice in range(0, len(linhas), linhas_por_pagina)
    ]


def _montar_stream_pagina(linhas):
    comandos = ["BT", "/F1 11 Tf", "50 800 Td", "14 TL"]
    for linha in linhas:
        comandos.append(f"({_limpar_texto_pdf(linha)}) Tj")
        comandos.append("T*")
    comandos.append("ET")
    return "\n".join(comandos)


def _limpar_texto_pdf(texto):
    seguro = str(texto).encode("latin-1", "replace").decode("latin-1")
    return seguro.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
