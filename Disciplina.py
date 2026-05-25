class Disciplina:
    def __init__(self, nome, codigo, carga_horaria, professor=None):
        self.nome = nome
        self.codigo = codigo
        self.carga_horaria = carga_horaria
        self.professor = None
        self.alunos = []

        if professor is not None:
            self.definir_professor(professor)

    def definir_professor(self, professor):
        self.professor = professor
        professor.adicionar_disciplina(self)

    def matricular_aluno(self, aluno):
        if aluno not in self.alunos:
            self.alunos.append(aluno)
            aluno.adicionar_disciplina(self)

    def listar_alunos(self):
        if not self.alunos:
            return "Nenhum aluno matriculado."

        return ", ".join(aluno.nome for aluno in self.alunos)

    def __str__(self):
        nome_professor = self.professor.nome if self.professor else "Sem professor"
        return (
            f"Disciplina: {self.nome} | Codigo: {self.codigo} | "
            f"Carga horaria: {self.carga_horaria}h | Professor: {nome_professor}"
        )
