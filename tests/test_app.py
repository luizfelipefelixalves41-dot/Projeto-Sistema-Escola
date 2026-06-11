import os
import tempfile
import unittest


TEST_DB = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite3")
TEST_DB.close()

os.environ["SQLITE_PATH"] = TEST_DB.name
os.environ["MYSQL_HOST"] = "127.0.0.1"
os.environ["MYSQL_PORT"] = "1"

import db  # noqa: E402

db._engine = "sqlite"

from app import app  # noqa: E402
from db import execute, fetch_one  # noqa: E402
from validators import cpf_valido  # noqa: E402


class SistemaAcademicoWebTest(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.client.get("/")

    def test_valida_cpf_com_digitos_verificadores(self):
        self.assertTrue(cpf_valido("529.982.247-25"))
        self.assertFalse(cpf_valido("111.111.111-11"))
        self.assertFalse(cpf_valido("123.456.789-00"))

    def test_nao_cadastra_aluno_com_cpf_invalido(self):
        antes = fetch_one("SELECT COUNT(*) AS total FROM alunos")["total"]
        resposta = self.client.post(
            "/alunos",
            data={
                "nome": "Teste CPF",
                "cpf": "111.111.111-11",
                "matricula": "TCPF001",
                "curso": "Testes",
            },
            follow_redirects=True,
        )
        depois = fetch_one("SELECT COUNT(*) AS total FROM alunos")["total"]

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(antes, depois)

    def test_bloqueia_aluno_duplicado(self):
        dados = {
            "nome": "Aluno Duplicado",
            "cpf": "529.982.247-25",
            "matricula": "TDUP001",
            "curso": "Testes",
        }
        self.client.post("/alunos", data=dados)
        self.client.post("/alunos", data=dados)

        total = fetch_one(
            "SELECT COUNT(*) AS total FROM alunos WHERE cpf = %s",
            ("529.982.247-25",),
        )["total"]
        self.assertEqual(total, 1)

    def test_arquiva_aluno_e_desativa_matriculas(self):
        aluno_id = execute(
            """
            INSERT INTO alunos (nome, cpf, matricula, curso)
            VALUES (%s, %s, %s, %s)
            """,
            ("Aluno Arquivo", "390.533.447-05", "TARQ001", "Testes"),
        )
        disciplina_id = execute(
            """
            INSERT INTO disciplinas (nome, codigo, carga_horaria)
            VALUES (%s, %s, %s)
            """,
            ("Disciplina Arquivo", "TARQ101", 40),
        )
        matricula_id = execute(
            """
            INSERT INTO matriculas (aluno_id, disciplina_id, ativo)
            VALUES (%s, %s, 1)
            """,
            (aluno_id, disciplina_id),
        )

        resposta = self.client.post(f"/alunos/{aluno_id}/arquivar", follow_redirects=True)
        aluno = fetch_one("SELECT ativo FROM alunos WHERE id = %s", (aluno_id,))
        matricula = fetch_one("SELECT ativo FROM matriculas WHERE id = %s", (matricula_id,))

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(aluno["ativo"], 0)
        self.assertEqual(matricula["ativo"], 0)


if __name__ == "__main__":
    unittest.main()
