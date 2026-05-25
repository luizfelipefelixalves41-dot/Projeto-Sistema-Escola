import os
import re
from io import BytesIO

from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from mysql.connector import Error

from db import IntegrityError, database_label, execute, fetch_all, fetch_one, is_sqlite
from relatorios import gerar_relatorio_json, gerar_relatorio_pdf


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "sistema-academico-dev")


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


def cpf_valido(cpf):
    return len(re.sub(r"\D", "", cpf)) == 11


def validar_cpf(cpf):
    if not cpf_valido(cpf):
        flash("Informe um CPF válido com 11 dígitos.", "warning")
        return False
    return True


def inteiro_positivo(valor, rotulo):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        flash(f"{rotulo} deve ser um número inteiro positivo.", "warning")
        return None

    if numero < 1:
        flash(f"{rotulo} deve ser maior que zero.", "warning")
        return None
    return numero


def registro_existe(tabela, registro_id):
    if not str(registro_id).isdigit():
        return False
    return fetch_one(f"SELECT id FROM {tabela} WHERE id = %s", (registro_id,)) is not None


def get_dashboard_counts():
    return {
        "alunos": fetch_one("SELECT COUNT(*) AS total FROM alunos")["total"],
        "professores": fetch_one("SELECT COUNT(*) AS total FROM professores")["total"],
        "disciplinas": fetch_one("SELECT COUNT(*) AS total FROM disciplinas")["total"],
        "matriculas": fetch_one(
            "SELECT COUNT(*) AS total FROM matriculas WHERE ativo = 1"
        )["total"],
    }


def get_dados_relatorio_banco():
    alunos = fetch_all(
        """
        SELECT id, nome, cpf, matricula, curso, criado_em
          FROM alunos
         ORDER BY nome
        """
    )
    professores = fetch_all(
        """
        SELECT id, nome, cpf, registro, area, criado_em
          FROM professores
         ORDER BY nome
        """
    )
    disciplinas = fetch_all(
        """
        SELECT d.id, d.nome, d.codigo, d.carga_horaria,
               COALESCE(p.nome, 'Sem professor') AS professor,
               d.criado_em
          FROM disciplinas d
          LEFT JOIN professores p ON p.id = d.professor_id
         ORDER BY d.nome
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
         ORDER BY d.nome, a.nome
        """
    )

    return {
        "banco": database_label(),
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
    counts = get_dashboard_counts()
    disciplinas = fetch_all(
        """
        SELECT d.id, d.nome, d.codigo, d.carga_horaria,
               COALESCE(p.nome, 'Sem professor') AS professor,
               COUNT(m.aluno_id) AS total_alunos
          FROM disciplinas d
          LEFT JOIN professores p ON p.id = d.professor_id
          LEFT JOIN matriculas m ON m.disciplina_id = d.id AND m.ativo = 1
         GROUP BY d.id, d.nome, d.codigo, d.carga_horaria, p.nome
         ORDER BY d.nome
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
            (
                ("nome", "Nome"),
                ("cpf", "CPF"),
                ("matricula", "Matrícula"),
                ("curso", "Curso"),
            )
        ) or not validar_cpf(form_text("cpf")):
            return redirect(url_for("alunos"))

        try:
            execute(
                """
                INSERT INTO alunos (nome, cpf, matricula, curso)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    form_text("nome"),
                    form_text("cpf"),
                    form_text("matricula"),
                    form_text("curso"),
                ),
            )
            flash("Aluno cadastrado com sucesso.", "success")
        except IntegrityError:
            flash("Já existe aluno com este CPF ou matrícula.", "warning")
        return redirect(url_for("alunos"))

    pesquisa = request.args.get("pesquisa", "").strip()
    filtro_nome = ""
    params = ()
    if pesquisa:
        filtro_nome = "WHERE LOWER(a.nome) LIKE LOWER(%s)"
        params = (f"%{pesquisa}%",)

    group_concat = "GROUP_CONCAT(d.nome, ', ')" if is_sqlite() else "GROUP_CONCAT(d.nome ORDER BY d.nome SEPARATOR ', ')"
    lista = fetch_all(
        f"""
        SELECT a.*,
               {group_concat} AS disciplinas
          FROM alunos a
          LEFT JOIN matriculas m ON m.aluno_id = a.id AND m.ativo = 1
          LEFT JOIN disciplinas d ON d.id = m.disciplina_id
         {filtro_nome}
         GROUP BY a.id
         ORDER BY a.nome
        """,
        params,
    )
    return render_template("alunos.html", alunos=lista, pesquisa=pesquisa)


@app.route("/alunos/<int:aluno_id>/editar", methods=["GET", "POST"])
def editar_aluno(aluno_id):
    aluno = fetch_one("SELECT * FROM alunos WHERE id = %s", (aluno_id,))
    if not aluno:
        flash("Aluno não encontrado.", "warning")
        return redirect(url_for("alunos"))

    if request.method == "POST":
        if not validar_campos_obrigatorios(
            (
                ("nome", "Nome"),
                ("cpf", "CPF"),
                ("matricula", "Matrícula"),
                ("curso", "Curso"),
            )
        ) or not validar_cpf(form_text("cpf")):
            return render_template("editar_aluno.html", aluno=aluno)

        try:
            execute(
                """
                UPDATE alunos
                   SET nome = %s, cpf = %s, matricula = %s, curso = %s
                 WHERE id = %s
                """,
                (
                    form_text("nome"),
                    form_text("cpf"),
                    form_text("matricula"),
                    form_text("curso"),
                    aluno_id,
                ),
            )
            flash("Aluno atualizado com sucesso.", "success")
            return redirect(url_for("alunos"))
        except IntegrityError:
            flash("Já existe aluno com este CPF ou matrícula.", "warning")

    return render_template("editar_aluno.html", aluno=aluno)


@app.route("/professores", methods=["GET", "POST"])
def professores():
    if request.method == "POST":
        if not validar_campos_obrigatorios(
            (
                ("nome", "Nome"),
                ("cpf", "CPF"),
                ("registro", "Registro"),
                ("area", "Área"),
            )
        ) or not validar_cpf(form_text("cpf")):
            return redirect(url_for("professores"))

        try:
            execute(
                """
                INSERT INTO professores (nome, cpf, registro, area)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    form_text("nome"),
                    form_text("cpf"),
                    form_text("registro"),
                    form_text("area"),
                ),
            )
            flash("Professor cadastrado com sucesso.", "success")
        except IntegrityError:
            flash("Já existe professor com este CPF ou registro.", "warning")
        return redirect(url_for("professores"))

    group_concat = "GROUP_CONCAT(d.nome, ', ')" if is_sqlite() else "GROUP_CONCAT(d.nome ORDER BY d.nome SEPARATOR ', ')"
    lista = fetch_all(
        f"""
        SELECT p.*,
               {group_concat} AS disciplinas
          FROM professores p
          LEFT JOIN disciplinas d ON d.professor_id = p.id
         GROUP BY p.id
         ORDER BY p.nome
        """
    )
    return render_template("professores.html", professores=lista)


@app.route("/professores/<int:professor_id>/editar", methods=["GET", "POST"])
def editar_professor(professor_id):
    professor = fetch_one("SELECT * FROM professores WHERE id = %s", (professor_id,))
    if not professor:
        flash("Professor não encontrado.", "warning")
        return redirect(url_for("professores"))

    if request.method == "POST":
        if not validar_campos_obrigatorios(
            (
                ("nome", "Nome"),
                ("cpf", "CPF"),
                ("registro", "Registro"),
                ("area", "Área"),
            )
        ) or not validar_cpf(form_text("cpf")):
            return render_template("editar_professor.html", professor=professor)

        try:
            execute(
                """
                UPDATE professores
                   SET nome = %s, cpf = %s, registro = %s, area = %s
                 WHERE id = %s
                """,
                (
                    form_text("nome"),
                    form_text("cpf"),
                    form_text("registro"),
                    form_text("area"),
                    professor_id,
                ),
            )
            flash("Professor atualizado com sucesso.", "success")
            return redirect(url_for("professores"))
        except IntegrityError:
            flash("Já existe professor com este CPF ou registro.", "warning")

    return render_template("editar_professor.html", professor=professor)


@app.route("/disciplinas", methods=["GET", "POST"])
def disciplinas():
    if request.method == "POST":
        professor_id = request.form.get("professor_id") or None
        carga_horaria = inteiro_positivo(form_text("carga_horaria"), "Carga horária")
        if not validar_campos_obrigatorios(
            (
                ("nome", "Nome"),
                ("codigo", "Código"),
                ("carga_horaria", "Carga horária"),
            )
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
                (
                    form_text("nome"),
                    form_text("codigo"),
                    carga_horaria,
                    professor_id,
                ),
            )
            flash("Disciplina cadastrada com sucesso.", "success")
        except IntegrityError:
            flash("Já existe disciplina com este código.", "warning")
        return redirect(url_for("disciplinas"))

    professores_lista = fetch_all("SELECT id, nome FROM professores ORDER BY nome")
    lista = fetch_all(
        """
        SELECT d.*, COALESCE(p.nome, 'Sem professor') AS professor,
               COUNT(m.aluno_id) AS total_alunos
          FROM disciplinas d
          LEFT JOIN professores p ON p.id = d.professor_id
          LEFT JOIN matriculas m ON m.disciplina_id = d.id AND m.ativo = 1
         GROUP BY d.id, p.nome
         ORDER BY d.nome
        """
    )
    return render_template(
        "disciplinas.html", disciplinas=lista, professores=professores_lista
    )


@app.route("/disciplinas/<int:disciplina_id>/editar", methods=["GET", "POST"])
def editar_disciplina(disciplina_id):
    disciplina = fetch_one("SELECT * FROM disciplinas WHERE id = %s", (disciplina_id,))
    if not disciplina:
        flash("Disciplina não encontrada.", "warning")
        return redirect(url_for("disciplinas"))

    professores_lista = fetch_all("SELECT id, nome FROM professores ORDER BY nome")

    if request.method == "POST":
        professor_id = request.form.get("professor_id") or None
        carga_horaria = inteiro_positivo(form_text("carga_horaria"), "Carga horária")
        if not validar_campos_obrigatorios(
            (
                ("nome", "Nome"),
                ("codigo", "Código"),
                ("carga_horaria", "Carga horária"),
            )
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
                (
                    form_text("nome"),
                    form_text("codigo"),
                    carga_horaria,
                    professor_id,
                    disciplina_id,
                ),
            )
            flash("Disciplina atualizada com sucesso.", "success")
            return redirect(url_for("disciplinas"))
        except IntegrityError:
            flash("Já existe disciplina com este código.", "warning")

    return render_template(
        "editar_disciplina.html",
        disciplina=disciplina,
        professores=professores_lista,
    )


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

    alunos_lista = fetch_all("SELECT id, nome, matricula FROM alunos ORDER BY nome")
    disciplinas_lista = fetch_all("SELECT id, nome, codigo FROM disciplinas ORDER BY nome")
    lista = fetch_all(
        """
        SELECT m.id, a.nome AS aluno, a.matricula, d.nome AS disciplina, d.codigo
          FROM matriculas m
          JOIN alunos a ON a.id = m.aluno_id
          JOIN disciplinas d ON d.id = m.disciplina_id
         WHERE m.ativo = 1
         ORDER BY d.nome, a.nome
        """
    )
    return render_template(
        "matriculas.html",
        alunos=alunos_lista,
        disciplinas=disciplinas_lista,
        matriculas=lista,
    )


@app.route("/matriculas/<int:matricula_id>/editar", methods=["GET", "POST"])
def editar_matricula(matricula_id):
    matricula = fetch_one("SELECT * FROM matriculas WHERE id = %s", (matricula_id,))
    if not matricula:
        flash("Matrícula não encontrada.", "warning")
        return redirect(url_for("matriculas"))

    alunos_lista = fetch_all("SELECT id, nome, matricula FROM alunos ORDER BY nome")
    disciplinas_lista = fetch_all("SELECT id, nome, codigo FROM disciplinas ORDER BY nome")

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
                (
                    aluno_id,
                    disciplina_id,
                    matricula_id,
                ),
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
    matricula = fetch_one("SELECT id FROM matriculas WHERE id = %s", (matricula_id,))
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
