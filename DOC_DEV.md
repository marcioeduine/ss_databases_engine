# DOC_DEV — Documentação Técnica do SS_DB Engine

Este documento descreve a arquitectura interna do motor, as responsabilidades de cada módulo, o fluxo de execução do REPL, como estender o sistema com novos comandos, e limitações/comportamentos conhecidos que qualquer pessoa a mexer no código deve ter em conta.

---

## Índice

1. [Visão geral da arquitectura](#1-visão-geral-da-arquitectura)
2. [Arquitectura de abstracção: Adapter Pattern](#2-arquitectura-de-abstracção-adapter-pattern)
3. [Gestão de sessões: SessionManager](#3-gestão-de-sessões-sessionmanager)
4. [Fluxo de execução do REPL](#4-fluxo-de-execução-do-repl)
5. [Responsabilidade de cada módulo](#5-responsabilidade-de-cada-módulo)
6. [Estado partilhado: `engine_config`](#6-estado-partilhado-engine_config)
7. [Como adicionar um novo comando](#7-como-adicionar-um-novo-comando)
8. [Como adicionar um novo driver de base de dados](#8-como-adicionar-um-novo-driver-de-base-de-dados)
9. [Comportamento de *commit* — macros vs. SQL bruto](#9-comportamento-de-commit--macros-vs-sql-bruto)
10. [Colisão de nomes entre macros e palavras-chave SQL](#10-colisão-de-nomes-entre-macros-e-palavras-chave-sql)
11. [Parser multi-instrução do `sql_engine.py`](#11-parser-multi-instrução-do-sql_enginepy)
12. [Exportação de dados — detalhes de implementação](#12-exportação-de-dados--detalhes-de-implementação)
13. [`Makefile` e empacotamento com PyInstaller](#13-makefile-e-empacotamento-com-pyinstaller)
14. [Limitações conhecidas e dívida técnica](#14-limitações-conhecidas-e-dívida-técnica)
15. [Sugestões de teste manual](#15-sugestões-de-teste-manual)

---

## 1. Visão geral da arquitectura

O projecto segue uma separação por responsabilidade, sem *packaging* formal (não existe `__init__.py` nem instalação via `pip`). Todos os módulos em `src/` são ficheiros Python planos que se importam uns aos outros por nome directo (`from utils import ...`), assumindo que são todos executados a partir do mesmo directório `src/`.

```
src/
├── cli.py                 # Ponto de entrada único; loop REPL e dispatch de comandos
├── db_drivers.py          # Camada de abstracção: BaseDatabaseDriver + adaptadores concretos
├── session_manager.py     # SessionManager + Session: gestão de múltiplas ligações activas
├── utils.py               # Funções transversais (histórico, peso da BD, impressão tabular)
├── config_commands.py     # config/settings/conf + help
├── schema_commands.py     # open, close, list, print, inspect/audit, .schema
├── export_commands.py     # export (csv/json/pdf)
├── data_commands.py       # update, rename, insert
└── sql_engine.py          # Execução de SQL bruto multi-instrução
```

O estado operacional é agora centralizado no `SessionManager`, que gere o mapa de sessões activas e expõe à interface os objectos `connection` e `cursor` de cada driver. Os módulos de comando (`schema_commands`, `data_commands`, etc.) continuam a receber `conn` e `cursor` como parâmetros explícitos — o `cli.py` simplesmente extrai esses valores da sessão activa antes de cada chamada.

---

## 2. Arquitectura de abstracção: Adapter Pattern

O motor usa o **Padrão de Adaptador (Adapter Pattern)** para desacoplar a interface do utilizador do motor de base de dados concreto.

```
                  ┌─────────────────────┐
                  │      cli.py         │  (apenas conhece SessionManager)
                  └──────────┬──────────┘
                             │
              ┌──────────────▼──────────────┐
              │       SessionManager        │  (gere o mapa de sessões)
              └──────────────┬──────────────┘
                             │ session.driver
              ┌──────────────▼──────────────┐
              │    BaseDatabaseDriver       │  (contrato abstracto — ABC)
              └──────────────┬──────────────┘
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  SQLiteDriver   │  │PostgreSQLDriver │  │  [futuro]       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### `BaseDatabaseDriver` (ABC)

Contrato público que todos os adaptadores devem implementar:

| Método | Assinatura | Descrição |
|---|---|---|
| `connect` | `(conn_string: str) -> bool` | Abre a ligação física ou de rede |
| `disconnect` | `() -> None` | Fecha todos os descritores activos |
| `list_entities` | `() -> list` | Devolve tabelas/colecções disponíveis |
| `fetch_data` | `(entity_name: str) -> tuple` | Devolve `(headers, rows)` |
| `insert_record` | `(entity_name: str, values: list) -> bool` | Executa uma inserção genérica |
| `entity_exists` | `(entity_name: str) -> bool` | Verifica se a entidade existe |

Além dos métodos, todos os adaptadores devem expor publicamente `self.connection` e `self.cursor` — estes são passados directamente aos módulos existentes (que não foram modificados) para manter compatibilidade.

---

## 3. Gestão de sessões: SessionManager

### `Session`

Estrutura de dados simples que encapsula uma ligação activa:

```python
class Session:
    alias: str                    # nome curto atribuído pelo utilizador
    driver: BaseDatabaseDriver    # adaptador concreto instanciado
    db_type: str                  # "sqlite", "postgres", "mongodb", ...
    db_name: str                  # caminho do ficheiro ou nome da BD remota
    active_table: Optional[str]   # tabela/colecção actualmente aberta com `open`
```

### `SessionManager`

Gere o dicionário `sessions: Dict[str, Session]` e o `active_alias: Optional[str]`.

Métodos públicos relevantes:

| Método | Descrição |
|---|---|
| `register_connection(alias, conn_string)` | Detecta o motor pelo prefixo, instancia o driver e regista a sessão |
| `switch_session(alias)` | Muda `active_alias` |
| `disconnect_session(alias)` | Chama `driver.disconnect()` e remove do dicionário; reatribui o foco |
| `get_active_session()` | Devolve o objecto `Session` activo, ou `None` |
| `list_sessions()` | Imprime o registo de sessões em formato tabular |
| `build_prompt(tx_active)` | Constrói a string de *prompt* completa |

### Resolução de driver por prefixo (`_resolve_driver`)

```python
if conn_string.startswith("postgresql://") or conn_string.startswith("postgres://"):
    return PostgreSQLDriver(), "postgres", db_name
if conn_string.startswith("mongodb://"):
    # avisa e devolve (None, None, None)
# fallback: SQLite
return SQLiteDriver(), "sqlite", conn_string
```

Para adicionar suporte a um novo motor, basta adicionar um ramo `if` aqui e uma nova subclasse de `BaseDatabaseDriver` em `db_drivers.py`.

---

## 4. Fluxo de execução do REPL

`cli.py::main()` faz o seguinte por cada iteração do loop:

1. Obtém a sessão activa via `session_manager.get_active_session()`.
2. Constrói o *prompt* via `session_manager.build_prompt(tx_active)`.
3. Lê uma linha com `input(prompt)`.
4. Faz *tokenização* com `shlex.split()` — isto respeita aspas simples/duplas, permitindo valores com espaços (ex.: `insert "Zeca da Silva" ...`).
5. Extrai `cmd = parts[0].lower()` e compara contra a lista de macros reservadas, num bloco `if/elif` sequencial.
6. Para comandos que **não** requerem sessão (`connect`, `use`, `sessions`, `disconnect`, `help`, `clear`, `config`, `exit`/`quit`), executa directamente.
7. Para todos os outros comandos, chama primeiro `_get_active_or_warn()` — se não houver sessão activa, emite erro e salta para o próximo ciclo.
8. Quando há sessão activa, extrai `session.driver.connection` e `session.driver.cursor` e passa-os às funções dos módulos existentes.
9. Se nada corresponder, cai no `else` final, que delega para `sql_engine.handle_raw_sql()`.

Importante: o *dispatch* é feito **apenas pela primeira palavra**. Isto tem uma implicação directa descrita na secção 10.

---

## 5. Responsabilidade de cada módulo

### `db_drivers.py`
- `BaseDatabaseDriver` — ABC com o contrato público.
- `SQLiteDriver` — adaptador para SQLite3 nativo (biblioteca padrão). Expõe `connection` e `cursor` directamente para compatibilidade com os módulos existentes.
- `PostgreSQLDriver` — adaptador para PostgreSQL via `psycopg2`. A importação de `psycopg2` está protegida por `try/except ImportError` com a *flag* `HAS_PSYCOPG2` — o motor arranca normalmente mesmo sem o pacote instalado; o erro só aparece ao tentar `connect postgresql://...`.

### `session_manager.py`
- `Session` — estrutura de dados de uma ligação activa.
- `SessionManager` — gere o mapa de sessões, o foco activo, o *prompt* dinâmico e a resolução de drivers.

### `utils.py`
- `initialise_cli_history()` — liga o histórico persistente (`~/.ss_sqlite_history`) via `readline`/`atexit`.
- `get_database_weight(db_name)` — calcula o tamanho em disco da base de dados, formatado em Bytes/KB/MB.
- `print_tabular_output(headers, rows)` — função central de formatação tabular, usada por praticamente todos os outros módulos. Calcula a largura de coluna dinamicamente a partir do conteúdo mais o cabeçalho.

### `config_commands.py`
- `handle_config_command(db_name, parts, engine_config)` — lê/escreve directamente as chaves de `engine_config` (excepto `in_transaction`, que está protegida contra alteração manual via `config`).
- `handle_help_command()` — imprime o menu de ajuda organizado por categorias.

### `schema_commands.py`
- `handle_open_command`, `handle_list_ls_command`, `handle_print_command`, `handle_inspect_command` — leitura/navegação de esquema, todos operando via `PRAGMA` e `sqlite_master`.
- `handle_schema_dot_command` — implementa `.schema`, indo directamente à coluna `sql` de `sqlite_master` para devolver o DDL original tal como foi escrito na criação da tabela.

### `export_commands.py`
- `handle_export_command` — normaliza formato/extensão e decide se o terceiro argumento é uma tabela ou uma *query* `SELECT` livre (`payload_source.strip().upper().startswith("SELECT")`).
- `_export_csv`, `_export_json`, `_export_pdf` — implementações privadas por formato. `_export_pdf` está protegida por `HAS_REPORTLAB` (import opcional em `try/except ImportError`).

### `data_commands.py`
- `handle_update_command` — assume sempre `WHERE id = ?`; não suporta actualizar por outra chave.
- `handle_rename_command` — dispatch interno consoante `current_table` e número de argumentos. Devolve o nome de tabela actualizado (ou `None`), que `cli.py` usa para actualizar `session.active_table`.
- `handle_insert_command` — introspecciona `PRAGMA table_info` para descobrir as colunas a preencher, excluindo automaticamente colunas `INTEGER PRIMARY KEY` (assumidas como auto-incrementadas). Faz conversão de tipo simples: `"null"` (case-insensitive) → `None`; strings só-dígitos → `int`; resto → `str`.

### `sql_engine.py`
- `handle_raw_sql` — recebe a linha de *input* completa (não tokenizada por `shlex`) e faz o seu próprio *parsing* carácter-a-carácter para separar múltiplas instruções SQL, usando `sqlite3.complete_statement()` para validar que um `;` é realmente o fim de uma instrução (e não parte de um literal). Ver secção 11.

### `cli.py`
- Orquestra tudo o resto. Instancia o `SessionManager`, gere o loop REPL e faz o *dispatch* de comandos. A lógica de `.dbload` está aqui inline (como atalho de sessão única), à semelhança de `begin`/`commit`/`rollback`.

---

## 6. Estado partilhado: `engine_config`

```python
engine_config = {
    "echo": False,
    "timer": False,
    "eqp": False,
    "stats": False,
    "in_transaction": False,
}
```

Este dicionário é passado por referência a quase todas as funções de comando. `in_transaction` é tratado como uma chave "especial", protegida explicitamente em `handle_config_command` para não poder ser alterada via `config in_transaction on` — só deve mudar através de `begin`/`commit`/`rollback` em `cli.py`.

Se adicionares uma nova *flag* de telemetria, basta:
1. Adicionar a chave a este dicionário com o valor por omissão.
2. Referenciá-la onde for relevante (normalmente `sql_engine.py`).
3. Actualizar `handle_help_command` em `config_commands.py`.

---

## 7. Como adicionar um novo comando

1. Escreve a função `handle_<nome>_command(...)` no módulo mais apropriado (ou cria um novo módulo, se for uma família de comandos nova).
2. Importa-a no topo de `cli.py`.
3. Adiciona um ramo `elif cmd == "<nome>":` no loop principal de `main()`, **antes** do `else` final que apanha SQL bruto.
4. Decide se o comando requer sessão activa ou não:
   - Se **não requer**: adiciona-o na secção "Universal commands" do loop.
   - Se **requer**: chama `_get_active_or_warn(session_manager)` e extrai `session.driver.connection`/`session.driver.cursor`.
5. Se o nome escolhido coincidir com uma palavra-chave SQL comum (`select`, `insert`, `update`, `delete`, `create`, `drop`, `alter`...), documenta isso claramente — criarás mais uma colisão (ver secção 10).
6. Actualiza `handle_help_command()` em `config_commands.py`.
7. Actualiza `DOC_USER.md` (secções correspondentes e a tabela de referência rápida) e este ficheiro, se a mudança for arquitectural.

---

## 8. Como adicionar um novo driver de base de dados

1. Em `db_drivers.py`, cria uma nova subclasse de `BaseDatabaseDriver` (ex.: `MongoDBDriver`).
2. Implementa os 6 métodos abstractos do contrato. Garante que `self.connection` e `self.cursor` ficam definidos após `connect()` — os módulos existentes dependem destas duas propriedades.
3. Em `session_manager.py`, no método `_resolve_driver`, adiciona um ramo `if` com o prefixo de detecção:

   ```python
   if conn_string.startswith("mongodb://"):
       db_name = conn_string.split("/")[-1] or conn_string
       return MongoDBDriver(), "mongodb", db_name
   ```

4. Importa o novo driver no topo de `session_manager.py`:

   ```python
   from db_drivers import BaseDatabaseDriver, SQLiteDriver, PostgreSQLDriver, MongoDBDriver
   ```

5. Actualiza `DOC_USER.md` (secção 3, tabela de motores suportados) e `README.md`.

---

## 9. Comportamento de *commit* — macros vs. SQL bruto

Isto é importante e fácil de esquecer ao mexer no código:

- **As macros de escrita** (`handle_update_command`, `handle_rename_command`, `handle_insert_command`) chamam `conn.commit()` explicitamente sempre que `engine_config["in_transaction"]` é `False`. Ou seja, fora de um bloco `begin`, cada operação destas grava-se sozinha.
- **`sql_engine.handle_raw_sql`** (o caminho para SQL bruto/livre) **não chama `conn.commit()` em nenhum ramo**. Isto significa que uma instrução `INSERT`/`UPDATE`/`DELETE` enviada directamente como SQL só fica persistida em disco se, a seguir, o utilizador escrever `commit` manualmente.
- Instruções DDL (`CREATE TABLE`, `DROP TABLE`, `ALTER TABLE`) via SQL bruto **persistem de imediato**, independentemente disto — não por qualquer lógica deste código, mas porque o módulo `sqlite3` da biblioteca padrão do Python não as inclui numa transacção implícita.

**Se isto for um comportamento intencional** (para forçar disciplina transaccional explícita em SQL livre), mantém-no. **Se não for intencional**, a correcção é simples: adicionar o mesmo padrão `if not engine_config["in_transaction"]: conn.commit()` dentro do loop de `handle_raw_sql`, depois de cada `cursor.execute(statement_stripped)` que não devolva `description` (ou seja, que não seja um `SELECT`).

---

## 10. Colisão de nomes entre macros e palavras-chave SQL

O *dispatcher* em `cli.py` decide entre macro e SQL bruto comparando apenas `parts[0].lower()` contra uma lista fixa de nomes reservados:

```
connect, use, sessions, connections, disconnect,
help, clear, cl, config, settings, configuration, conf,
.dbload, open, close, list, ls, print, inspect, audit,
.schema, export, update, rename, insert,
begin, commit, rollback, exit, quit
```

Como `insert` e `update` são também palavras-chave SQL padrão, qualquer instrução SQL bruta que comece literalmente por `INSERT` ou `UPDATE` **nunca chega a `sql_engine.py`** — é sempre capturada primeiro pela macro homónima.

**Duas formas de resolver isto, se decidires corrigir:**

a) **Verificação de intenção antes do dispatch** — em `cli.py`, antes de comparar `cmd` contra a lista de macros, verificar se a linha completa parece uma instrução SQL válida terminada em `;` ou reconhecida por `sqlite3.complete_statement()`, e nesse caso saltar directamente para `handle_raw_sql`.

b) **Renomear as macros conflituosas** — por exemplo, `insert` → `add`, `update` → `upd`. Resolve a ambiguidade de raiz, mas é uma mudança que quebra compatibilidade com *scripts*/hábitos já existentes.

---

## 11. Parser multi-instrução do `sql_engine.py`

`handle_raw_sql` implementa a sua própria segmentação de instruções, carácter-a-carácter:

```python
for char in user_input:
    current_accumulator.append(char)
    if char == ';':
        candidate_string = "".join(current_accumulator)
        if sqlite3.complete_statement(candidate_string):
            statements.append(candidate_string.strip())
            current_accumulator = []
```

`sqlite3.complete_statement()` é a função certa para isto — sabe distinguir um `;` que termina de facto uma instrução de um `;` que está dentro de um literal de string (`'a;b'`) ou de um comentário. Qualquer resto de *input* sem `;` final é adicionado como última instrução (permite executar uma única instrução sem ponto-e-vírgula, tal como o `sqlite3` CLI oficial permite).

Cada instrução da lista é depois executada sequencialmente no mesmo `for statement_stripped in statements:`, com telemetria (`echo`, `eqp`, `timer`, `stats`) aplicada individualmente a cada uma. **Atenção:** se uma instrução no meio da lista falhar (excepção capturada), a função faz `return` imediato — as instruções seguintes na mesma linha **não** são executadas.

---

## 12. Exportação de dados — detalhes de implementação

- CSV e JSON usam apenas a biblioteca padrão (`csv`, `json`).
- PDF usa `reportlab.platypus` (`SimpleDocTemplate`, `Table`, `TableStyle`, `Paragraph`) — cada célula é envolvida num `Paragraph` (não texto simples), especificamente para obter quebra automática de linha em células longas.
- O `import` de `reportlab` está protegido por `try/except ImportError` no topo do módulo, com a *flag* `HAS_REPORTLAB` a controlar se `_export_pdf` sequer tenta correr.
- `handle_export_command` decide tabela-vs-*query* verificando se o *payload*, depois de `strip().upper()`, começa por `"SELECT"`. Isto significa que uma *query* começada por `WITH` (CTE) **não** é reconhecida como *query* livre — seria tratada como nome de tabela literal e falharia. Se precisares de exportar CTEs, terás de ajustar esta condição para também aceitar `"WITH"`.

---

## 13. `Makefile` e empacotamento com PyInstaller

```makefile
NAME      = ss_sqlite_cli
DB        = database.db
SQL       = sqlite3
SQLFLAGS  = -column -header
PY_MAIN   = src/cli.py
SRC       = table_list.sql

all: $(DB)
$(DB): $(SRC)
	$(SQL) $(SQLFLAGS) $(DB) < $(SRC)

fclean:
	rm -rf ./build ./dist ./$(NAME).spec $(DB)

re: fclean all

run: $(SRC) $(DB)
	@$(PY_MAIN) $(DB)

build:
	pyinstaller --onefile --name=$(NAME) $(PY_MAIN)
```

- `make all` — depende do binário `sqlite3` (linha de comandos oficial) estar instalado no sistema, apenas para popular `database.db` a partir de `table_list.sql`. **Não é uma dependência do motor Python em si** — é só conveniência de desenvolvimento/demonstração.
- `make run` — assume `$(PY_MAIN)` (`src/cli.py`) tem permissão de execução (`chmod +x`) e usa `#!/usr/bin/env python3` como *shebang* (já presente no ficheiro). Cria automaticamente uma sessão `default` com `database.db`.
- `make build` — empacota `src/cli.py` e todos os módulos que importa num único executável *standalone* via `PyInstaller`. Como os módulos são importados por nome directo (sem serem um pacote formal), o `PyInstaller` só os inclui correctamente se forem descobertos automaticamente a partir do mesmo directório de `cli.py`. Os novos módulos `db_drivers.py` e `session_manager.py` são importados transitivamente e serão incluídos automaticamente.
- `make fclean` — limpa artefactos de *build* (`build/`, `dist/`, `.spec`) e a base de dados de demonstração.
- `make re` — atalho para `fclean` seguido de `all`.

---

## 14. Limitações conhecidas e dívida técnica

| # | Limitação | Impacto | Ficheiro(s) |
|---|---|---|---|
| 1 | SQL bruto começado por `INSERT`/`UPDATE` é capturado pelas macros homónimas (secção 10) | Utilizador não consegue escrever `INSERT INTO`/`UPDATE` SQL puro directamente | `cli.py` |
| 2 | `handle_raw_sql` nunca faz `conn.commit()` (secção 9) | `DELETE`/`INSERT`/`UPDATE` via SQL bruto exigem `commit` manual explícito | `sql_engine.py` |
| 3 | `handle_export_command` só reconhece `SELECT` como *query* livre, não `WITH` (CTE) | Exportar o resultado de uma CTE falha ou é mal interpretado como nome de tabela | `export_commands.py` |
| 4 | `handle_update_command` assume sempre `WHERE id = ?` | Tabelas sem coluna `id`, ou com chave primária de outro nome, não são suportadas | `data_commands.py` |
| 5 | `make all`/`make build` dependem de ferramentas externas (`sqlite3` CLI, `pyinstaller`) não verificadas antes de correr | Falha com erro genérico de shell (`command not found`) em vez de mensagem clara | `Makefile` |
| 6 | `PostgreSQLDriver.fetch_data` e os módulos `schema_commands`/`sql_engine` usam sintaxe SQLite (PRAGMA, `sqlite_master`, `sqlite3.complete_statement`) | Comandos como `inspect`, `.schema` e SQL bruto multi-instrução não funcionam correctamente sobre sessões PostgreSQL | `schema_commands.py`, `sql_engine.py` |
| 7 | Mudar de sessão com `use` enquanto uma transacção está activa não faz `rollback` automático na sessão anterior | Utilizador pode perder o fio transaccional ao saltar entre sessões sem confirmar/cancelar | `cli.py` |

Nenhuma destas limitações foi corrigida nesta revisão — ficam aqui registadas para decisão e priorização futura.

---

## 15. Sugestões de teste manual

Sequência mínima para validar uma alteração ao motor:

```bash
make re                        # regenerar database.db a partir de table_list.sql
python3 src/cli.py database.db
```

Dentro da shell — fluxo SQLite completo:

```
help
sessions
config
ls
open sstable
list
print
.schema
inspect
insert "Zeca" 900000002 "Som" "Ana" "Cabo"
print
update cliente 1 "Mariana"
print cliente
export csv teste sstable
export json teste sstable
export pdf teste sstable
begin
update cliente 2 "Teste TX"
rollback
print cliente
close
rename sstable outra_tabela
ls
```

Teste de sessões múltiplas:

```
connect mem :memory:
sessions
use mem
ls
use default
disconnect mem
sessions
.dbload :memory:
ls
exit
```

Confirma sempre, após qualquer alteração a `sql_engine.py` ou às macros de escrita, se as alterações **persistem** ao reabrir o mesmo ficheiro de base de dados numa nova invocação do processo — é a forma mais directa de apanhar regressões no comportamento de *commit* descrito na secção 9.
