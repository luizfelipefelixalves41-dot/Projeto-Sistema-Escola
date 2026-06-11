# Sistema Acadêmico Web

Interface web em Flask para cadastrar alunos, professores, disciplinas e
matrículas usando MySQL.

Se o MySQL não estiver instalado ou iniciado, a aplicação usa automaticamente
um banco SQLite local chamado `sistema_academico.sqlite3`, permitindo testar a
interface sem travar na conexão.

## Funcionalidades

- Cadastro, edição, busca e paginação de alunos, professores e disciplinas.
- Matrícula de alunos em disciplinas.
- Bloqueio de matrícula duplicada.
- Validação real de CPF pelos dígitos verificadores.
- Arquivamento lógico de alunos, professores e disciplinas.
- Remoção lógica de matrículas mantendo histórico no banco.
- Relatórios em JSON e PDF com resumo e status dos registros.
- Fallback automático para SQLite em ambiente de desenvolvimento.
- Testes automatizados com `unittest`.

## Requisitos

- Python 3.10 ou superior.
- MySQL Server, caso queira usar o banco principal.
- Terminal PowerShell, Prompt de Comando, Bash ou equivalente.

## 1. Criar e ativar ambiente virtual

No Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

No Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Instalar dependências

```bash
python -m pip install -r requirements.txt
```

## 3. Criar o banco MySQL

No MySQL, execute:

```bash
mysql -u root -p < schema.sql
```

O script cria o banco `sistema_academico`, as tabelas e alguns dados iniciais.
O usuário usado no comando precisa ter permissão para criar banco, tabelas e
inserir dados.

Se o banco já existir de uma versão anterior, a aplicação tenta adicionar
automaticamente as colunas de arquivamento ao iniciar.

## 4. Configurar conexão

Por padrão, a aplicação usa:

```text
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=sistema_academico
```

No Windows PowerShell:

```powershell
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="sua_senha"
$env:MYSQL_DATABASE="sistema_academico"
```

No Linux/macOS:

```bash
export MYSQL_USER=root
export MYSQL_PASSWORD=sua_senha
export MYSQL_DATABASE=sistema_academico
```

## 5. Rodar a interface

```bash
python app.py
```

Depois acesse:

```text
http://127.0.0.1:5000
```

## 6. Rodar os testes

```bash
python -m unittest discover -s tests
```

## Modo SQLite local

Se o MySQL não estiver disponível, a aplicação usa SQLite automaticamente. Para
obrigar o uso do MySQL e desativar o fallback SQLite:

No Windows PowerShell:

```powershell
$env:MYSQL_REQUIRED="1"
python app.py
```

No Linux/macOS:

```bash
MYSQL_REQUIRED=1 python app.py
```

## Configurações para produção

Antes de publicar o sistema fora do ambiente de desenvolvimento:

- Defina `FLASK_SECRET_KEY` com uma chave segura.
- Defina `MYSQL_REQUIRED=1` para evitar uso acidental do SQLite.
- Configure `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD` e `MYSQL_DATABASE`.
- Não use senha do banco diretamente no código.
- Use um servidor WSGI apropriado para produção.
- Deixe `FLASK_DEBUG` desativado. O debug só liga se `FLASK_DEBUG=1`.

## Arquivos principais

- `app.py`: rotas da aplicação Flask.
- `db.py`: conexão, fallback SQLite e adaptação simples do schema.
- `validators.py`: validações de CPF, números e paginação.
- `schema.sql`: criação do banco MySQL e tabelas.
- `templates/`: telas HTML.
- `static/styles.css`: estilo visual da interface.
- `relatorios.py`: geração de relatórios JSON e PDF.
- `tests/`: testes automatizados.
