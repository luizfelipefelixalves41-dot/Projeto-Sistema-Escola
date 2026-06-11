import os
from io import BytesIO

from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from mysql.connector import Error

from db import IntegrityError, database_label, execute, fetch_all, fetch_one, is_sqlite
from relatorios import gerar_relatorio_json, gerar_relatorio_pdf
from validators import cpf_valido, inteiro_positivo, normalizar_cpf, pagina_atual


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "sistema-academico-dev")

ITENS_POR_PAGINA = 8


def debug_enabled():
    return os.getenv("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}


def form_text(name):
    return request.form.get(name, "").strip()


def validar_campos_obrigatorios(campos):
    vazios = [rotulo for nome, rotulo in campos if not form_text(nome)]
    if vazios:
        flash(f"Preencha os campos obrigatórios: {', '.join(vazios)}.", "warning")
        return False
    return True


def validar_cpf_formulario(cpf):
    if not cpf_valido(cpf):
        flash("Informe um CPF válido.", "warning")
        return False
    return True


def validar_inteiro_positivo(valor, rotulo):
    numero = inteiro_positivo(valor)
    if numero is None:
        flash(f"{rotulo} deve ser um número inteiro positivo.", "warning")
    return numero


def registro_existe(tabela, registro_id, somente_ativos=True):
    if not str(registro_id).isdigit():
        return False
    filtro_ativo = " AND ativo = 1" if somente_ativos else ""
    return fetch_one(
        f"SELECT id FROM {tabela} WHERE id = %s{filtro_ativo}",
        (registro_id,),
    ) is not None


def get_paginacao(total, pagina):
    paginas = max((total + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA, 1)
    pagina = min(pagina, paginas)
    return {
        "pagina": pagina,
        "paginas": paginas,
        "total": total,
        "offset": (pagina - 1) * ITENS_POR_PAGINA,
        "tem_anterior": pagina > 1,
        "tem_proxima": pagina < paginas,
    }


def pagina_parametro():
    return pagina_atual(request.args.get("pagina"))


def filtro_like(campo, termo):
    if not termo:
        return "", []
    return f" AND LOWER({campo}) LIKE LOWER(%s)", [f"%{termo}%"]


def mensagem_integridade(tabela, campos):
    for campo, valor, rotulo in campos:
        if valor and fetch_one(
            f"SELECT id FROM {tabela} WHERE {campo} = %s",
            (valor,),
        ):
            return f"{rotulo} já cadastrado."
    return "Já existe um registro com dados únicos iguais."


def get_dashboard_counts():
    return {
        "alunos": fetch_one("SELECT COUNT(*) AS total FROM alunos WHERE ativo = 1")["total"],
        "professores": fetch_one(
            "SELECT COUNT(*) AS total FROM professores WHERE ativo = 1"
        )["total"],
        "disciplinas": fetch_one(
            "SELECT COUNT(*) AS total FROM disciplinas WHERE ativo = 1"
        )["total"],
        "matriculas": fetch_one(
            "SELECT COUNT(*) AS total FROM matriculas WHERE ativo = 1"
        )["total"],
    }


def get_dados_relatorio_banco():
    alunos = fetch_all(
        """
        SELECT id, nome, cpf, matricula, curso,
               CASE WHEN ativo = 1 THEN 'ativo' ELSE 'arquivado' END AS status,
               criado_em, arquivado_em
          FROM alunos
         ORDER BY ativo DESC, nome
        """
    )
    professores = fetch_all(
        """
        SELECT id, nome, cpf, registro, area,
               CASE WHEN ativo = 1 THEN 'ativo' ELSE 'arquivado' END AS status,
               criado_em, arquivado_em
          FROM professores
         ORDER BY ativo DESC, nome
        """
    )
    disciplinas = fetch_all(
        """
        SELECT d.id, d.nome, d.codigo, d.carga_horaria,
               COALESCE(p.nome, 'Sem professor') AS professor,
               CASE WHEN d.ativo = 1 THEN 'ativa' ELSE 'arquivada' END AS status,
               d.criado_em, d.arquivado_em
          FROM disciplinas d
          LEFT JOIN professores p ON p.id = d.professor_id AND p.ativo = 1
         ORDER BY d.ativo DESC, d.nome
        """
    )
    matriculas = fetch_all(
        """
        SELECT m.id, a.nome AS aluno, a.matricula,
               d.nome AS disciplina, d.codigo,
               CASE WHEN m.ativo = 1 THEN 'ativa' ELSE 'removida' END AS status,
               m.criado_em, m.removido_em
          FROM matriculas m
          JOIN alunos a ON a.id = m.aluno_id
          JOIN disciplinas d ON d.id = m.disciplina_id
         ORDER BY m.ativo DESC, d.nome, a.nome
        """
    )

    resumo = {
        "alunos_ativos": sum(1 for aluno in alunos if aluno["status"] == "ativo"),
        "professores_ativos": sum(
            1 for professor in professores if professor["status"] == "ativo"
        ),
        "disciplinas_ativas": sum(
            1 for disciplina in disciplinas if disciplina["status"] == "ativa"
        ),
        "matriculas_ativas": sum(
            1 for matricula in matriculas if matricula["status"] == "ativa"
        ),
    }

    return {
        "banco": database_label(),
        "resumo": resumo,
        "alunos": alunos,
        "professores": professores,
        "disciplinas": disciplinas,
        "matriculas": matriculas,
    }


@app.errorhandler(Error)
def handle_database_error(error):
    return render_template("erro.html", error=error), 500


@app.route("/")
def index():
    return render_template("entrada.html")


@app.route("/painel")
def painel():
    counts = get_dashboard_counts()
    disciplinas = fetch_all(
        """
        SELECT d.id, d.nome, d.codigo, d.carga_horaria,
               COALESCE(p.nome, 'Sem professor') AS professor,
               COUNT(m.aluno_id) AS total_alunos
          FROM disciplinas d
          LEFT JOIN professores p ON p.id = d.professor_id AND p.ativo = 1
          LEFT JOIN matriculas m ON m.disciplina_id = d.id AND m.ativo = 1
         WHERE d.ativo = 1
         GROUP BY d.id, d.nome, d.codigo, d.carga_horaria, p.nome
         ORDER BY d.nome
         LIMIT 6
        """
    )
    return render_template(
        "index.html",
        counts=counts,
        database_label=database_label(),
        disciplinas=disciplinas,
    )


@app.get("/relatorios/json")
def baixar_relatorio_json():
    conteudo = gerar_relatorio_json(get_dados_relatorio_banco())
    return send_file(
        BytesIO(conteudo.encode("utf-8")),
        mimetype="application/json",
        as_attachment=True,
        download_name="relatorio_academico.json",
    )


@app.get("/relatorios/pdf")
def baixar_relatorio_pdf():
    conteudo = gerar_relatorio_pdf(get_dados_relatorio_banco())
    return send_file(
        BytesIO(conteudo),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="relatorio_academico.pdf",
    )


@app.route("/alunos", methods=["GET", "POST"])
def alunos():
    if request.method == "POST":
        if not validar_campos_obrigatorios(
            (("nome", "Nome"), ("cpf", "CPF"), ("matricula", "Matrícula"), ("curso", "Curso"))
        ) or not validar_cpf_formulario(form_text("cpf")):
            return redirect(url_for("alunos"))

        cpf = normalizar_cpf(form_text("cpf"))
        try:
            execute(
                """
                INSERT INTO alunos (nome, cpf, matricula, curso)
                VALUES (%s, %s, %s, %s)
                """,
                (form_text("nome"), cpf, form_text("matricula"), form_text("curso")),
            )
            flash("Aluno cadastrado com sucesso.", "success")
        except IntegrityError:
            flash(
                mensagem_integridade(
                    "alunos",
                    (("cpf", cpf, "CPF"), ("matricula", form_text("matricula"), "Matrícula")),
                ),
                "warning",
            )
        return redirect(url_for("alunos"))

    pesquisa = request.args.get("pesquisa", "").strip()
    pagina = pagina_parametro()
    filtro, params = filtro_like("a.nome", pesquisa)
    total = fetch_one(
        f"SELECT COUNT(*) AS total FROM alunos a WHERE a.ativo = 1{filtro}",
        params,
    )["total"]
    paginacao = get_paginacao(total, pagina)
    group_concat = (
        "GROUP_CONCAT(d.nome, ', ')"
        if is_sqlite()
        else "GROUP_CONCAT(d.nome ORDER BY d.nome SEPARATOR ', ')"
    )
    lista = fetch_all(
        f"""
        SELECT a.*,
               {group_concat} AS disciplinas
          FROM alunos a
          LEFT JOIN matriculas m ON m.aluno_id = a.id AND m.ativo = 1
          LEFT JOIN disciplinas d ON d.id = m.disciplina_id AND d.ativo = 1
         WHERE a.ativo = 1{filtro}
         GROUP BY a.id
         ORDER BY a.nome
         LIMIT %s OFFSET %s
        """,
        tuple(params + [ITENS_POR_PAGINA, paginacao["offset"]]),
    )
    return render_template(
        "alunos.html",
        alunos=lista,
        pesquisa=pesquisa,
        paginacao=paginacao,
    )


@app.route("/alunos/<int:aluno_id>/editar", methods=["GET", "POST"])
def editar_aluno(aluno_id):
    aluno = fetch_one("SELECT * FROM alunos WHERE id = %s AND ativo = 1", (aluno_id,))
    if not aluno:
        flash("Aluno não encontrado.", "warning")
        return redirect(url_for("alunos"))

    if request.method == "POST":
        if not validar_campos_obrigatorios(
            (("nome", "Nome"), ("cpf", "CPF"), ("matricula", "Matrícula"), ("curso", "Curso"))
        ) or not validar_cpf_formulario(form_text("cpf")):
            return render_template("editar_aluno.html", aluno=aluno)

        cpf = normalizar_cpf(form_text("cpf"))
        try:
            execute(
                """
                UPDATE alunos
                   SET nome = %s, cpf = %s, matricula = %s, curso = %s
                 WHERE id = %s
                """,
                (form_text("nome"), cpf, form_text("matricula"), form_text("curso"), aluno_id),
            )
            flash("Aluno atualizado com sucesso.", "success")
            return redirect(url_for("alunos"))
        except IntegrityError:
            flash("CPF ou matrícula já cadastrados para outro aluno.", "warning")

    return render_template("editar_aluno.html", aluno=aluno)


@app.post("/alunos/<int:aluno_id>/arquivar")
def arquivar_aluno(aluno_id):
    if not registro_existe("alunos", aluno_id):
        flash("Aluno não encontrado.", "warning")
        return redirect(url_for("alunos"))
    execute("UPDATE alunos SET ativo = 0, arquivado_em = CURRENT_TIMESTAMP WHERE id = %s", (aluno_id,))
    execute(
        "UPDATE matriculas SET ativo = 0, removido_em = CURRENT_TIMESTAMP WHERE aluno_id = %s",
        (aluno_id,),
    )
    flash("Aluno arquivado e matrículas ativas removidas da interface.", "success")
    return redirect(url_for("alunos"))


@app.route("/professores", methods=["GET", "POST"])
def professores():
    if request.method == "POST":
        if not validar_campos_obrigatorios(
            (("nome", "Nome"), ("cpf", "CPF"), ("registro", "Registro"), ("area", "Área"))
        ) or not validar_cpf_formulario(form_text("cpf")):
            return redirect(url_for("professores"))

        cpf = normalizar_cpf(form_text("cpf"))
        try:
            execute(
                """
                INSERT INTO professores (nome, cpf, registro, area)
                VALUES (%s, %s, %s, %s)
                """,
                (form_text("nome"), cpf, form_text("registro"), form_text("area")),
            )
            flash("Professor cadastrado com sucesso.", "success")
        except IntegrityError:
            flash(
                mensagem_integridade(
                    "professores",
                    (("cpf", cpf, "CPF"), ("registro", form_text("registro"), "Registro")),
                ),
                "warning",
            )
        return redirect(url_for("professores"))

    pesquisa = request.args.get("pesquisa", "").strip()
    pagina = pagina_parametro()
    filtro, params = filtro_like("p.nome", pesquisa)
    total = fetch_one(
        f"SELECT COUNT(*) AS total FROM professores p WHERE p.ativo = 1{filtro}",
        params,
    )["total"]
    paginacao = get_paginacao(total, pagina)
    group_concat = (
        "GROUP_CONCAT(d.nome, ', ')"
        if is_sqlite()
        else "GROUP_CONCAT(d.nome ORDER BY d.nome SEPARATOR ', ')"
    )
    lista = fetch_all(
        f"""
        SELECT p.*,
               {group_concat} AS disciplinas
          FROM professores p
          LEFT JOIN disciplinas d ON d.professor_id = p.id AND d.ativo = 1
         WHERE p.ativo = 1{filtro}
         GROUP BY p.id
         ORDER BY p.nome
         LIMIT %s OFFSET %s
        """,
        tuple(params + [ITENS_POR_PAGINA, paginacao["offset"]]),
    )
    return render_template(
        "professores.html",
        professores=lista,
        pesquisa=pesquisa,
        paginacao=paginacao,
    )


@app.route("/professores/<int:professor_id>/editar", methods=["GET", "POST"])
def editar_professor(professor_id):
    professor = fetch_one(
        "SELECT * FROM professores WHERE id = %s AND ativo = 1",
        (professor_id,),
    )
    if not professor:
        flash("Professor não encontrado.", "warning")
        return redirect(url_for("professores"))

    if request.method == "POST":
        if not validar_campos_obrigatorios(
            (("nome", "Nome"), ("cpf", "CPF"), ("registro", "Registro"), ("area", "Área"))
        ) or not validar_cpf_formulario(form_text("cpf")):
            return render_template("editar_professor.html", professor=professor)

        cpf = normalizar_cpf(form_text("cpf"))
        try:
            execute(
                """
                UPDATE professores
                   SET nome = %s, cpf = %s, registro = %s, area = %s
                 WHERE id = %s
                """,
                (form_text("nome"), cpf, form_text("registro"), form_text("area"), professor_id),
            )
            flash("Professor atualizado com sucesso.", "success")
            return redirect(url_for("professores"))
        except IntegrityError:
            flash("CPF ou registro já cadastrados para outro professor.", "warning")

    return render_template("editar_professor.html", professor=professor)


@app.post("/professores/<int:professor_id>/arquivar")
def arquivar_professor(professor_id):
    if not registro_existe("professores", professor_id):
        flash("Professor não encontrado.", "warning")
        return redirect(url_for("professores"))
    execute(
        "UPDATE professores SET ativo = 0, arquivado_em = CURRENT_TIMESTAMP WHERE id = %s",
        (professor_id,),
    )
    execute("UPDATE disciplinas SET professor_id = NULL WHERE professor_id = %s", (professor_id,))
    flash("Professor arquivado. As disciplinas ficaram sem professor definido.", "success")
    return redirect(url_for("professores"))


@app.route("/disciplinas", methods=["GET", "POST"])
def disciplinas():
    if request.method == "POST":
        professor_id = request.form.get("professor_id") or None
        carga_horaria = validar_inteiro_positivo(form_text("carga_horaria"), "Carga horária")
        if not validar_campos_obrigatorios(
            (("nome", "Nome"), ("codigo", "Código"), ("carga_horaria", "Carga horária"))
        ) or carga_horaria is None:
            return redirect(url_for("disciplinas"))
        if professor_id and not registro_existe("professores", professor_id):
            flash("Professor selecionado não foi encontrado.", "warning")
            return redirect(url_for("disciplinas"))

        try:
            execute(
                """
                INSERT INTO disciplinas (nome, codigo, carga_horaria, professor_id)
                VALUES (%s, %s, %s, %s)
                """,
                (form_text("nome"), form_text("codigo"), carga_horaria, professor_id),
            )
            flash("Disciplina cadastrada com sucesso.", "success")
        except IntegrityError:
            flash("Código já cadastrado para outra disciplina.", "warning")
        return redirect(url_for("disciplinas"))

    pesquisa = request.args.get("pesquisa", "").strip()
    pagina = pagina_parametro()
    filtro, params = filtro_like("d.nome", pesquisa)
    total = fetch_one(
        f"SELECT COUNT(*) AS total FROM disciplinas d WHERE d.ativo = 1{filtro}",
        params,
    )["total"]
    paginacao = get_paginacao(total, pagina)
    professores_lista = fetch_all(
        "SELECT id, nome FROM professores WHERE ativo = 1 ORDER BY nome"
    )
    lista = fetch_all(
        f"""
        SELECT d.*, COALESCE(p.nome, 'Sem professor') AS professor,
               COUNT(m.aluno_id) AS total_alunos
          FROM disciplinas d
          LEFT JOIN professores p ON p.id = d.professor_id AND p.ativo = 1
          LEFT JOIN matriculas m ON m.disciplina_id = d.id AND m.ativo = 1
         WHERE d.ativo = 1{filtro}
         GROUP BY d.id, p.nome
         ORDER BY d.nome
         LIMIT %s OFFSET %s
        """,
        tuple(params + [ITENS_POR_PAGINA, paginacao["offset"]]),
    )
    return render_template(
        "disciplinas.html",
        disciplinas=lista,
        professores=professores_lista,
        pesquisa=pesquisa,
        paginacao=paginacao,
    )


@app.route("/disciplinas/<int:disciplina_id>/editar", methods=["GET", "POST"])
def editar_disciplina(disciplina_id):
    disciplina = fetch_one(
        "SELECT * FROM disciplinas WHERE id = %s AND ativo = 1",
        (disciplina_id,),
    )
    if not disciplina:
        flash("Disciplina não encontrada.", "warning")
        return redirect(url_for("disciplinas"))

    professores_lista = fetch_all(
        "SELECT id, nome FROM professores WHERE ativo = 1 ORDER BY nome"
    )

    if request.method == "POST":
        professor_id = request.form.get("professor_id") or None
        carga_horaria = validar_inteiro_positivo(form_text("carga_horaria"), "Carga horária")
        if not validar_campos_obrigatorios(
            (("nome", "Nome"), ("codigo", "Código"), ("carga_horaria", "Carga horária"))
        ) or carga_horaria is None:
            return render_template(
                "editar_disciplina.html",
                disciplina=disciplina,
                professores=professores_lista,
            )
        if professor_id and not registro_existe("professores", professor_id):
            flash("Professor selecionado não foi encontrado.", "warning")
            return render_template(
                "editar_disciplina.html",
                disciplina=disciplina,
                professores=professores_lista,
            )

        try:
            execute(
                """
                UPDATE disciplinas
                   SET nome = %s, codigo = %s, carga_horaria = %s, professor_id = %s
                 WHERE id = %s
                """,
                (form_text("nome"), form_text("codigo"), carga_horaria, professor_id, disciplina_id),
            )
            flash("Disciplina atualizada com sucesso.", "success")
            return redirect(url_for("disciplinas"))
        except IntegrityError:
            flash("Código já cadastrado para outra disciplina.", "warning")

    return render_template(
        "editar_disciplina.html",
        disciplina=disciplina,
        professores=professores_lista,
    )


@app.post("/disciplinas/<int:disciplina_id>/arquivar")
def arquivar_disciplina(disciplina_id):
    if not registro_existe("disciplinas", disciplina_id):
        flash("Disciplina não encontrada.", "warning")
        return redirect(url_for("disciplinas"))
    execute(
        "UPDATE disciplinas SET ativo = 0, arquivado_em = CURRENT_TIMESTAMP WHERE id = %s",
        (disciplina_id,),
    )
    execute(
        "UPDATE matriculas SET ativo = 0, removido_em = CURRENT_TIMESTAMP WHERE disciplina_id = %s",
        (disciplina_id,),
    )
    flash("Disciplina arquivada e matrículas ativas removidas da interface.", "success")
    return redirect(url_for("disciplinas"))


@app.route("/matriculas", methods=["GET", "POST"])
def matriculas():
    if request.method == "POST":
        aluno_id = form_text("aluno_id")
        disciplina_id = form_text("disciplina_id")
        if not aluno_id or not disciplina_id:
            flash("Selecione um aluno e uma disciplina.", "warning")
            return redirect(url_for("matriculas"))
        if not registro_existe("alunos", aluno_id):
            flash("Aluno selecionado não foi encontrado.", "warning")
            return redirect(url_for("matriculas"))
        if not registro_existe("disciplinas", disciplina_id):
            flash("Disciplina selecionada não foi encontrada.", "warning")
            return redirect(url_for("matriculas"))

        matricula_existente = fetch_one(
            """
            SELECT id, ativo
              FROM matriculas
             WHERE aluno_id = %s AND disciplina_id = %s
            """,
            (aluno_id, disciplina_id),
        )

        if matricula_existente and matricula_existente["ativo"]:
            flash("Este aluno já está matriculado nessa disciplina.", "warning")
        elif matricula_existente:
            execute(
                """
                UPDATE matriculas
                   SET ativo = 1, removido_em = NULL
                 WHERE id = %s
                """,
                (matricula_existente["id"],),
            )
            flash("Matrícula reativada com sucesso.", "success")
        else:
            try:
                execute(
                    """
                    INSERT INTO matriculas (aluno_id, disciplina_id, ativo)
                    VALUES (%s, %s, 1)
                    """,
                    (aluno_id, disciplina_id),
                )
                flash("Aluno matriculado com sucesso.", "success")
            except IntegrityError:
                flash("Este aluno já está matriculado nessa disciplina.", "warning")
        return redirect(url_for("matriculas"))

    pesquisa = request.args.get("pesquisa", "").strip()
    pagina = pagina_parametro()
    filtro, params = filtro_like("a.nome", pesquisa)
    alunos_lista = fetch_all(
        "SELECT id, nome, matricula FROM alunos WHERE ativo = 1 ORDER BY nome"
    )
    disciplinas_lista = fetch_all(
        "SELECT id, nome, codigo FROM disciplinas WHERE ativo = 1 ORDER BY nome"
    )
    total = fetch_one(
        f"""
        SELECT COUNT(*) AS total
          FROM matriculas m
          JOIN alunos a ON a.id = m.aluno_id AND a.ativo = 1
          JOIN disciplinas d ON d.id = m.disciplina_id AND d.ativo = 1
         WHERE m.ativo = 1{filtro}
        """,
        params,
    )["total"]
    paginacao = get_paginacao(total, pagina)
    lista = fetch_all(
        f"""
        SELECT m.id, a.nome AS aluno, a.matricula, d.nome AS disciplina, d.codigo
          FROM matriculas m
          JOIN alunos a ON a.id = m.aluno_id AND a.ativo = 1
          JOIN disciplinas d ON d.id = m.disciplina_id AND d.ativo = 1
         WHERE m.ativo = 1{filtro}
         ORDER BY d.nome, a.nome
         LIMIT %s OFFSET %s
        """,
        tuple(params + [ITENS_POR_PAGINA, paginacao["offset"]]),
    )
    return render_template(
        "matriculas.html",
        alunos=alunos_lista,
        disciplinas=disciplinas_lista,
        matriculas=lista,
        pesquisa=pesquisa,
        paginacao=paginacao,
    )


@app.route("/matriculas/<int:matricula_id>/editar", methods=["GET", "POST"])
def editar_matricula(matricula_id):
    matricula = fetch_one("SELECT * FROM matriculas WHERE id = %s AND ativo = 1", (matricula_id,))
    if not matricula:
        flash("Matrícula não encontrada.", "warning")
        return redirect(url_for("matriculas"))

    alunos_lista = fetch_all(
        "SELECT id, nome, matricula FROM alunos WHERE ativo = 1 ORDER BY nome"
    )
    disciplinas_lista = fetch_all(
        "SELECT id, nome, codigo FROM disciplinas WHERE ativo = 1 ORDER BY nome"
    )

    if request.method == "POST":
        aluno_id = form_text("aluno_id")
        disciplina_id = form_text("disciplina_id")
        if not aluno_id or not disciplina_id:
            flash("Selecione um aluno e uma disciplina.", "warning")
            return render_template(
                "editar_matricula.html",
                matricula=matricula,
                alunos=alunos_lista,
                disciplinas=disciplinas_lista,
            )
        if not registro_existe("alunos", aluno_id):
            flash("Aluno selecionado não foi encontrado.", "warning")
            return render_template(
                "editar_matricula.html",
                matricula=matricula,
                alunos=alunos_lista,
                disciplinas=disciplinas_lista,
            )
        if not registro_existe("disciplinas", disciplina_id):
            flash("Disciplina selecionada não foi encontrada.", "warning")
            return render_template(
                "editar_matricula.html",
                matricula=matricula,
                alunos=alunos_lista,
                disciplinas=disciplinas_lista,
            )

        try:
            execute(
                """
                UPDATE matriculas
                   SET aluno_id = %s, disciplina_id = %s, ativo = 1, removido_em = NULL
                 WHERE id = %s
                """,
                (aluno_id, disciplina_id, matricula_id),
            )
            flash("Matrícula atualizada com sucesso.", "success")
            return redirect(url_for("matriculas"))
        except IntegrityError:
            flash("Este aluno já está matriculado nessa disciplina.", "warning")

    return render_template(
        "editar_matricula.html",
        matricula=matricula,
        alunos=alunos_lista,
        disciplinas=disciplinas_lista,
    )


@app.post("/matriculas/<int:matricula_id>/excluir")
def excluir_matricula(matricula_id):
    matricula = fetch_one("SELECT id FROM matriculas WHERE id = %s AND ativo = 1", (matricula_id,))
    if not matricula:
        flash("Matrícula não encontrada.", "warning")
        return redirect(url_for("matriculas"))

    execute(
        """
        UPDATE matriculas
           SET ativo = 0, removido_em = CURRENT_TIMESTAMP
         WHERE id = %s
        """,
        (matricula_id,),
    )
    flash("Matrícula removida da interface. O registro continua no banco.", "success")
    return redirect(url_for("matriculas"))


if __name__ == "__main__":
    app.run(debug=debug_enabled())
