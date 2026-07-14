# SS - Databases Engine — REPL Interactivo para Administração de Bases de Dados

`SS_DB Engine` é uma shell interactiva (REPL — *Read-Eval-Print Loop*) escrita em Python 3, pensada para administração, exploração e depuração rápida de bases de dados a partir da linha de comandos. Combina macros de alto nível (navegação de tabelas, exportação, inserção assistida) com acesso directo a SQL puro, gestão de múltiplas sessões em simultâneo e telemetria de execução configurável em tempo real.

O motor suporta múltiplos motores de bases de dados através de uma **arquitectura de abstracção por adaptadores (Adapter Pattern)**: o utilizador opera sempre com os mesmos comandos, independentemente de estar ligado a um ficheiro SQLite local, a uma instância PostgreSQL em rede, ou a qualquer outro motor suportado no futuro.

Este README dá uma visão geral rápida do projecto. Para instruções detalhadas de utilização, consulta o **[DOC_USER.md](DOC_USER.md)**; para a arquitectura interna, decisões técnicas e como estender o motor, consulta o **[DOC_DEV.md](DOC_DEV.md)**.

---

## Funcionalidades principais

- **Suporte multi-motor** — o mesmo conjunto de comandos funciona sobre SQLite, PostgreSQL e (no futuro) MongoDB ou outros motores, sem que o utilizador precise de conhecer dialectos ou *drivers* específicos.
- **Gestão de múltiplas sessões** — `connect`, `use`, `sessions` e `disconnect` permitem abrir várias ligações a bases de dados distintas e saltar entre elas sem sair da shell.
- **Prompt dinâmico contextual** — o *prompt* reflecte sempre o tipo de motor, o alias da sessão activa e a tabela/colecção aberta:
  ```
  SS_DB [sqlite::local] (sstable)>
  SS_DB [postgres::prod] (customers)>
  ```
- **Navegação contextual de tabelas** — `open <tabela>` fixa a shell num contexto de tabela específico, simplificando comandos subsequentes (`print`, `insert`, `update`, `list`).
- **Ligação dinâmica a bases de dados** — `.dbload <ficheiro.db>` troca a base de dados activa sem reiniciar o processo; se nenhum ficheiro for indicado no arranque, o motor abre em modo neutro e aguarda um `connect`.
- **Inspecção estrutural profunda** — `inspect`/`audit` audita índices e chaves estrangeiras; `.schema` extrai a instrução DDL nativa (`CREATE TABLE ...`) de qualquer tabela.
- **Telemetria e profiling configuráveis** (via `config`):
  - `echo` — ecoa o *input* bruto recebido pela shell.
  - `timer` — mede o tempo de execução de cada instrução com precisão de microssegundos.
  - `eqp` — encaminha automaticamente `SELECT`/`WITH` através do `EXPLAIN QUERY PLAN` do motor SQLite.
  - `stats` — reporta contagem de páginas, tamanho de página, páginas livres e peso em disco da base activa.
- **Motor de SQL bruto multi-instrução** — aceita várias instruções SQL separadas por `;` numa única linha, respeitando literais de string (não parte a instrução em pontos-e-vírgulas dentro de aspas).
- **Exportação nativa multi-formato** — `export <csv|json|pdf> <ficheiro> <tabela|SELECT ...>` serializa qualquer tabela ou resultado de *query* directamente para CSV, JSON estruturado, ou PDF vectorizado em A4 (via `reportlab`).
- **Fronteiras transaccionais explícitas** — `begin` / `commit` / `rollback` para agrupar alterações estruturais em blocos atómicos.
- **Histórico persistente de comandos** — histórico da shell gravado em `~/.ss_sqlite_history` via `readline`, preservado entre sessões.
- **Inserção dinâmica e segura** — `insert <valores...>` calcula automaticamente as colunas alvo (ignorando chaves primárias auto-incrementadas) e converte tipos (`NULL`, inteiros, texto).
- **Compilação para binário standalone** — alvo `make build` empacota o motor num executável único via `PyInstaller`.

---

## Motores suportados

| Motor | Tipo | Driver Python | Estado |
|---|---|---|---|
| **SQLite** | Relacional (embutido) | `sqlite3` (nativo) | ✅ Completo |
| **PostgreSQL** | Relacional (servidor) | `psycopg2` (opcional) | ✅ Suportado |
| **MongoDB** | NoSQL (documentos) | `pymongo` | 🔜 Previsto |

---

## Requisitos

- **Python 3.8+** (o motor usa apenas a biblioteca padrão para SQLite; bibliotecas adicionais para outros motores são opcionais).
- **`sqlite3`** (o binário de linha de comandos, usado apenas pelo `Makefile` para popular a base de dados inicial a partir de `table_list.sql`).
- **`psycopg2-binary`** — obrigatório apenas para ligar a instâncias PostgreSQL:

  ```bash
  python3 -m pip install --user psycopg2-binary
  ```

- **`reportlab`** — obrigatório apenas para `export pdf`:

  ```bash
  python3 -m pip install --user reportlab
  ```

- **`pyinstaller`** — opcional, necessário apenas para `make build`:

  ```bash
  python3 -m pip install --user pyinstaller
  ```

---

## Arranque rápido

```bash
# Gerar a base de dados de exemplo a partir de table_list.sql
make all

# Correr o motor sobre essa base de dados (sessão 'default' criada automaticamente)
make run

# Ou correr directamente com o interpretador Python
python3 src/cli.py database.db

# Arrancar sem argumentos → aguarda um 'connect' explícito dentro da shell
python3 src/cli.py
```

Dentro da shell, exemplos de uso multi-sessão:

```
SS_DB> connect local database.db
SS_DB [sqlite::local]> connect prod postgresql://user:pass@192.168.1.50/billing
SS_DB [sqlite::local]> use prod
SS_DB [postgres::prod]> ls
SS_DB [postgres::prod]> open customers
SS_DB [postgres::prod] (customers)> print
```

Escreve `help` a qualquer momento para consultar o menu de comandos disponíveis.

---

## Estrutura do projecto

```
.
├── .gitignore
├── LICENSE
├── Makefile                   # Alvos: all, clean, fclean, re, run, build
├── README.md                  # Este ficheiro
├── DOC_USER.md                # Manual do utilizador (todos os comandos, exemplos, fluxos)
├── DOC_DEV.md                 # Documentação técnica (arquitectura, extensão, limitações)
├── table_list.sql             # Script de exemplo usado por `make all`
└── src/
    ├── cli.py                 # Ponto de entrada: loop REPL, dispatch de comandos e SessionManager
    ├── db_drivers.py          # Camada de abstracção: BaseDatabaseDriver, SQLiteDriver, PostgreSQLDriver
    ├── session_manager.py     # SessionManager: gestão de múltiplas sessões e prompt dinâmico
    ├── utils.py               # Histórico persistente, peso da BD, impressão tabular
    ├── config_commands.py     # Comandos `config`/`settings` e `help`
    ├── schema_commands.py     # `open`, `close`, `list`, `print`, `inspect`, `.schema`
    ├── export_commands.py     # `export` (CSV / JSON / PDF)
    ├── data_commands.py       # `update`, `rename`, `insert`
    └── sql_engine.py          # Execução de SQL bruto multi-instrução, com hooks de telemetria
```

---

## Aviso de compatibilidade

Alguns comandos SQL padrão partilham o nome com macros internas da shell (`insert`, `update`). Quando escreves uma instrução SQL bruta cuja primeira palavra coincide com uma dessas macros, a shell interpreta-a como a macro, não como SQL. Consulta a secção **"Colisão entre macros e palavras-chave SQL"** do [DOC_USER.md](DOC_USER.md) para contornares esta limitação.

---

## Licence

This project is licensed under the GNU General Public Licence v3 — see the [LICENSE](LICENSE) file for complete architecture protection and compliance details.
