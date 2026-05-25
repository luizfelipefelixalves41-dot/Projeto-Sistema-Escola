from Aluno import Aluno
from Disciplina import Disciplina
from Professor import Professor
from relatorios import gerar_relatorio_json, gerar_relatorio_pdf


class SistemaAcademico:
    def __init__(self):
        self.alunos = []
        self.professores = []
        self.disciplinas = []

    def cadastrar_aluno(self, aluno):
        self.alunos.append(aluno)

    def cadastrar_professor(self, professor):
        self.professores.append(professor)

    def cadastrar_disciplina(self, disciplina):
        self.disciplinas.append(disciplina)

    def buscar_aluno_por_matricula(self, matricula):
        for aluno in self.alunos:
            if aluno.matricula == matricula:
                return aluno
        return None

    def pesquisar_alunos_por_nome(self, nome):
        termo = nome.strip().lower()
        if not termo:
            return self.alunos

        return [aluno for aluno in self.alunos if termo in aluno.nome.lower()]

    def buscar_professor_por_registro(self, registro):
        for professor in self.professores:
            if professor.registro == registro:
                return professor
        return None

    def buscar_disciplina_por_codigo(self, codigo):
        for disciplina in self.disciplinas:
            if disciplina.codigo == codigo:
                return disciplina
        return None

    def matricular_aluno_em_disciplina(self, matricula, codigo_disciplina):
        aluno = self.buscar_aluno_por_matricula(matricula)
        disciplina = self.buscar_disciplina_por_codigo(codigo_disciplina)

        if aluno is None:
            print("Aluno nao encontrado.")
            return

        if disciplina is None:
            print("Disciplina nao encontrada.")
            return

        disciplina.matricular_aluno(aluno)
        print(f"{aluno.nome} foi matriculado em {disciplina.nome}.")

    def editar_aluno(self, matricula, nome=None, cpf=None, nova_matricula=None, curso=None):
        aluno = self.buscar_aluno_por_matricula(matricula)
        if aluno is None:
            print("Aluno nao encontrado.")
            return False

        if nome is not None:
            aluno.nome = nome
        if cpf is not None:
            aluno.cpf = cpf
        if nova_matricula is not None:
            aluno.matricula = nova_matricula
        if curso is not None:
            aluno.curso = curso

        print("Aluno atualizado com sucesso.")
        return True

    def editar_professor(self, registro, nome=None, cpf=None, novo_registro=None, area=None):
        professor = self.buscar_professor_por_registro(registro)
        if professor is None:
            print("Professor nao encontrado.")
            return False

        if nome is not None:
            professor.nome = nome
        if cpf is not None:
            professor.cpf = cpf
        if novo_registro is not None:
            professor.registro = novo_registro
        if area is not None:
            professor.area = area

        print("Professor atualizado com sucesso.")
        return True

    def editar_disciplina(
        self,
        codigo,
        nome=None,
        novo_codigo=None,
        carga_horaria=None,
        professor=None,
    ):
        disciplina = self.buscar_disciplina_por_codigo(codigo)
        if disciplina is None:
            print("Disciplina nao encontrada.")
            return False

        if nome is not None:
            disciplina.nome = nome
        if novo_codigo is not None:
            disciplina.codigo = novo_codigo
        if carga_horaria is not None:
            disciplina.carga_horaria = carga_horaria
        if professor is not None:
            disciplina.definir_professor(professor)

        print("Disciplina atualizada com sucesso.")
        return True

    def listar_alunos(self):
        print("\nALUNOS")
        for aluno in self.alunos:
            print(aluno)
            print(f"Disciplinas: {aluno.listar_disciplinas()}")

    def listar_professores(self):
        print("\nPROFESSORES")
        for professor in self.professores:
            print(professor)
            print(f"Disciplinas: {professor.listar_disciplinas()}")

    def listar_disciplinas(self):
        print("\nDISCIPLINAS")
        for disciplina in self.disciplinas:
            print(disciplina)
            print(f"Alunos: {disciplina.listar_alunos()}")

    def gerar_dados_relatorio(self):
        return {
            "alunos": [
                {
                    "nome": aluno.nome,
                    "cpf": aluno.cpf,
                    "matricula": aluno.matricula,
                    "curso": aluno.curso,
                    "disciplinas": [disciplina.nome for disciplina in aluno.disciplinas],
                }
                for aluno in self.alunos
            ],
            "professores": [
                {
                    "nome": professor.nome,
                    "cpf": professor.cpf,
                    "registro": professor.registro,
                    "area": professor.area,
                    "disciplinas": [
                        disciplina.nome for disciplina in professor.disciplinas
                    ],
                }
                for professor in self.professores
            ],
            "disciplinas": [
                {
                    "nome": disciplina.nome,
                    "codigo": disciplina.codigo,
                    "carga_horaria": disciplina.carga_horaria,
                    "professor": (
                        disciplina.professor.nome
                        if disciplina.professor
                        else "Sem professor"
                    ),
                    "alunos": [aluno.nome for aluno in disciplina.alunos],
                }
                for disciplina in self.disciplinas
            ],
            "matriculas": [
                {
                    "aluno": aluno.nome,
                    "matricula": aluno.matricula,
                    "disciplina": disciplina.nome,
                    "codigo": disciplina.codigo,
                    "status": "ativa",
                }
                for disciplina in self.disciplinas
                for aluno in disciplina.alunos
            ],
        }

    def gerar_relatorio_json(self, caminho="relatorio_academico.json"):
        return gerar_relatorio_json(self.gerar_dados_relatorio(), caminho)

    def gerar_relatorio_pdf(self, caminho="relatorio_academico.pdf"):
        return gerar_relatorio_pdf(self.gerar_dados_relatorio(), caminho)


def main():
    sistema = SistemaAcademico()

    professor = Professor(
        nome="Mariana Souza",
        cpf="111.222.333-44",
        registro="PROF001",
        area="Programacao",
    )

    aluno_1 = Aluno(
        nome="Felipe Santos",
        cpf="555.666.777-88",
        matricula="2026001",
        curso="Sistemas de Informacao",
    )
    aluno_2 = Aluno(
        nome="Ana Lima",
        cpf="999.888.777-66",
        matricula="2026002",
        curso="Ciencia da Computacao",
    )

    disciplina = Disciplina(
        nome="Programacao Orientada a Objetos",
        codigo="POO101",
        carga_horaria=80,
        professor=professor,
    )

    sistema.cadastrar_professor(professor)
    sistema.cadastrar_aluno(aluno_1)
    sistema.cadastrar_aluno(aluno_2)
    sistema.cadastrar_disciplina(disciplina)

    sistema.matricular_aluno_em_disciplina("2026001", "POO101")
    sistema.matricular_aluno_em_disciplina("2026002", "POO101")

    sistema.listar_professores()
    sistema.listar_alunos()
    sistema.listar_disciplinas()
    sistema.gerar_relatorio_json()
    sistema.gerar_relatorio_pdf()


if __name__ == "__main__":
    main()
