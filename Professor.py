from Pessoa import Pessoa


class Professor(Pessoa):
    def __init__(self, nome, cpf, registro, area):
        super().__init__(nome, cpf)
        self.registro = registro
        self.area = area
        self.disciplinas = []

    def adicionar_disciplina(self, disciplina):
        if disciplina not in self.disciplinas:
            self.disciplinas.append(disciplina)

    def listar_disciplinas(self):
        if not self.disciplinas:
            return "Nenhuma disciplina atribuida."

        return ", ".join(disciplina.nome for disciplina in self.disciplinas)

    def __str__(self):
        return (
            f"Professor: {self.nome} | CPF: {self.cpf} | "
            f"Registro: {self.registro} | Area: {self.area}"
        )
