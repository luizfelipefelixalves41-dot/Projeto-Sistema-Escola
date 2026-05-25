CREATE DATABASE IF NOT EXISTS sistema_academico
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE sistema_academico;

CREATE TABLE IF NOT EXISTS alunos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(120) NOT NULL,
  cpf VARCHAR(20) NOT NULL UNIQUE,
  matricula VARCHAR(30) NOT NULL UNIQUE,
  curso VARCHAR(120) NOT NULL,
  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS professores (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(120) NOT NULL,
  cpf VARCHAR(20) NOT NULL UNIQUE,
  registro VARCHAR(30) NOT NULL UNIQUE,
  area VARCHAR(120) NOT NULL,
  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS disciplinas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(120) NOT NULL,
  codigo VARCHAR(30) NOT NULL UNIQUE,
  carga_horaria INT NOT NULL,
  professor_id INT NULL,
  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_disciplinas_professor
    FOREIGN KEY (professor_id) REFERENCES professores(id)
    ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS matriculas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  aluno_id INT NOT NULL,
  disciplina_id INT NOT NULL,
  ativo TINYINT(1) NOT NULL DEFAULT 1,
  removido_em TIMESTAMP NULL,
  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_aluno_disciplina (aluno_id, disciplina_id),
  CONSTRAINT fk_matriculas_aluno
    FOREIGN KEY (aluno_id) REFERENCES alunos(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_matriculas_disciplina
    FOREIGN KEY (disciplina_id) REFERENCES disciplinas(id)
    ON DELETE CASCADE
);

INSERT IGNORE INTO professores (nome, cpf, registro, area)
VALUES ('Mariana Souza', '111.222.333-44', 'PROF001', 'Programacao');

INSERT IGNORE INTO alunos (nome, cpf, matricula, curso)
VALUES
  ('Felipe Santos', '555.666.777-88', '2026001', 'Sistemas de Informacao'),
  ('Ana Lima', '999.888.777-66', '2026002', 'Ciencia da Computacao');

INSERT IGNORE INTO disciplinas (nome, codigo, carga_horaria, professor_id)
SELECT 'Programacao Orientada a Objetos', 'POO101', 80, id
  FROM professores
 WHERE registro = 'PROF001';

INSERT IGNORE INTO matriculas (aluno_id, disciplina_id)
SELECT a.id, d.id
  FROM alunos a
  JOIN disciplinas d ON d.codigo = 'POO101'
 WHERE a.matricula IN ('2026001', '2026002');
