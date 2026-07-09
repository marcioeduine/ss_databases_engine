# DOC_DEV — Documentação Técnica do SS_SQLite

Este documento descreve a arquitectura interna do motor, as responsabilidades de cada módulo, o fluxo de execução do REPL, como estender o sistema com novos comandos, e limitações/comportamentos conhecidos que qualquer pessoa a mexer no código deve ter em conta.

---

## Índice

1. [Visão geral da arquitectura](#1-visão-geral-da-arquitectura)
2. [Fluxo de execução do REPL](#2-fluxo-de-execução-do-repl)
3. [Responsabilidade de cada módulo](#3-responsabilidade-de-cada-módulo)
4. [Estado partilhado: `engine_config`](#4-estado-partilhado-engine_config)
5. [Como adicionar um novo comando](#5-como-adicionar-um-novo-comando)
6. [Comportamento de *commit* — macros vs. SQL bruto](#6-comportamento-de-commit--macros-vs-sql-bruto)
7. [Colisão de nomes entre macros e palavras-chave SQL](#7-colisão-de-nomes-entre-macros-e-palavras-chave-sql)
8. [Parser multi-instrução do `sql_engine.py`](#8-parser-multi-instrução-do-sql_enginepy)
9. [Exportação de dados — detalhes de implementação](#9-exportação-de-dados--detalhes-de-implementação)
10. [`Makefile` e empacotamento com PyInstaller](#10-makefile-e-empacotamento-com-pyinstaller)
11. [Limitações conhecidas e dívida técnica](#11-limitações-conhecidas-e-dívida-técnica)
12. [Sugestões de teste manual](#12-sugestões-de-teste-manual)

---

## 1. Visão geral da arquitectura

O projecto segue uma separação simples por responsabilidade, sem *packaging* formal (não existe `__init__.py` nem instalação via `pip`). Todos os módulos em `src/` são ficheiros Python planos que se importam uns aos outros por nome directo (`from utils import ...`), assumindo que são todos executados a partir do mesmo directório `src/`.

```
src/
├── cli.py                # Ponto de entrada único; loop REPL e dispatch de comandos
├── utils.py                # Funções transversais (histórico, peso da BD, impressão tabular)
├── config_commands.py       # config/settings/conf + help
├── schema_commands.py         # open, close, list, print, inspect/audit, .schema
├── export_commands.py           # export (csv/json/pdf)
├── data_commands.py               # update, rename, insert
└── sql_engine.py                    # Execução de SQL bruto multi-instrução
```

Não há classes — o estado é passado explicitamente entre funções através de:
- `conn` (`sqlite3.Connection`)
- `cursor` (`sqlite3.Cursor`)
- `current_table` (`str | None`)
- `engine_config` (`dict`)

Esta escolha mantém cada módulo testável isoladamente (basta injectar um cursor/ligação de teste) e evita estado global oculto.

---

## 2. Fluxo de execução do REPL

`cli.py::main()` faz o seguinte, por cada iteração do loop:

1. Constrói o *prompt* consoante `current_table` e `engine_config["in_transaction"]`.
2. Lê uma linha com `input(prompt)`.
3. Faz *tokenização* com `shlex.split()` — isto respeita aspas simples/duplas, permitindo valores com espaços (ex.: `insert "Zeca da Silva" ...`).
4. Extrai `cmd = parts[0].lower()` e compara contra a lista de macros reservadas, num bloco `if/elif` sequencial.
5. Se nada corresponder, cai no `else` final, que delega para `sql_engine.handle_raw_sql()` — tratando o *input* completo (não apenas `parts`) como uma ou mais instruções SQL.

Importante: o *dispatch* é feito **apenas pela primeira palavra**. Isto tem uma implicação directa descrita na secção 7.

---

## 3. Responsabilidade de cada módulo

### `utils.py`
- `initialise_cli_history()` — liga o histórico persistente (`~/.ss_sqlite_history`) via `readline`/`atexit`.
- `get_database_weight(db_name)` — calcula o tamanho em disco da base de dados, formatado em Bytes/KB/MB.
- `print_tabular_output(headers, rows)` — função central de formatação tabular, usada por praticamente todos os outros módulos. Calcula a largura de coluna dinamicamente a partir do conteúdo mais o cabeçalho.

### `config_commands.py`
- `handle_config_command(db_name, parts, engine_config)` — lê/escreve directamente as chaves de `engine_config` (excepto `in_transaction`, que está protegida contra alteração manual via `config`).
- `handle_help_command()` — imprime o menu de ajuda estático. **Nota:** este menu ainda não inclui `.dbload` nem `.schema` — foram adicionados depois do texto de ajuda ser escrito. Actualiza `handle_help_command()` sempre que adicionares/renomeares um comando.

### `schema_commands.py`
- `handle_open_command`, `handle_list_ls_command`, `handle_print_command`, `handle_inspect_command` — leitura/navegação de esquema, todos operando via `PRAGMA` e `sqlite_master`.
- `handle_schema_dot_command` — implementa `.schema`, indo directamente à coluna `sql` de `sqlite_master` para devolver o DDL original tal como foi escrito na criação da tabela.

### `export_commands.py`
- `handle_export_command` — normaliza formato/extensão e decide se o terceiro argumento é uma tabela ou uma query `SELECT` livre (`payload_source.strip().upper().startswith("SELECT")`).
- `_export_csv`, `_export_json`, `_export_pdf` — implementações privadas por formato. `_export_pdf` está protegida por `HAS_REPORTLAB` (import opcional em `try/except ImportError`), para o motor continuar a funcionar em ambientes sem `reportlab` instalado.

### `data_commands.py`
- `handle_update_command` — assume sempre `WHERE id = ?`; não suporta actualizar por outra chave.
- `handle_rename_command` — dispatch interno consoante `current_table` e número de argumentos (ver tabela na secção 5 do DOC_USER.md). Devolve o nome de tabela actualizado (ou `None`), que `cli.py` usa para actualizar `current_table`.
- `handle_insert_command` — introspecciona `PRAGMA table_info` para descobrir as colunas a preencher, excluindo automaticamente colunas `INTEGER PRIMARY KEY` (assumidas como auto-incrementadas). Faz conversão de tipo simples: `"null"` (case-insensitive) → `None`; strings só-dígitos → `int`; resto → `str`.

### `sql_engine.py`
- `handle_raw_sql` — recebe a linha de *input* completa (não tokenizada por `shlex`) e o faz o seu próprio parsing carácter-a-carácter para separar múltiplas instruções SQL, usando `sqlite3.complete_statement()` para validar que um `;` é realmente o fim de uma instrução (e não parte de um literal). Ver secção 8.

### `cli.py`
- Orquestra tudo o resto; contém a lógica de `.dbload` inline (não extraída para módulo próprio, ao contrário de outros comandos).

---

## 4. Estado partilhado: `engine_config`

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
3. Actualizar `handle_config_command` (mostra automaticamente todas as chaves excepto `in_transaction`, por isso normalmente não precisas de tocar lá) e `handle_help_command`.

---

## 5. Como adicionar um novo comando

1. Escreve a função `handle_<nome>_command(...)` no módulo mais apropriado (ou cria um novo módulo, se for uma família de comandos nova).
2. Importa-a no topo de `cli.py`.
3. Adiciona um ramo `elif cmd == "<nome>":` no loop principal de `main()`, **antes** do `else` final que apanha SQL bruto.
4. Se o nome escolhido coincidir com uma palavra-chave SQL comum (`select`, `insert`, `update`, `delete`, `create`, `drop`, `alter`...), documenta isso claramente — vais criar mais uma colisão (ver secção 7).
5. Actualiza `handle_help_command()` em `config_commands.py`.
6. Actualiza `DOC_USER.md` (secções 3–5 e a tabela de referência rápida na secção 13) e este ficheiro, se a mudança for arquitectural.

---

## 6. Comportamento de *commit* — macros vs. SQL bruto

Isto é importante e fácil de esquecer ao mexer no código:

- **As macros de escrita** (`handle_update_command`, `handle_rename_command`, `handle_insert_command`) chamam `conn.commit()` explicitamente sempre que `engine_config["in_transaction"]` é `False`. Ou seja, fora de um bloco `begin`, cada operação destas grava-se sozinha.
- **`sql_engine.handle_raw_sql`** (o caminho para SQL bruto/livre) **não chama `conn.commit()` em nenhum ramo**. Isto significa que uma instrução `INSERT`/`UPDATE`/`DELETE` enviada directamente como SQL só fica persistida em disco se, a seguir, o utilizador escrever `commit` manualmente (dentro ou fora de um bloco `begin` explícito).
- Instruções DDL (`CREATE TABLE`, `DROP TABLE`, `ALTER TABLE`) via SQL bruto **persistem de imediato**, independentemente disto — não por qualquer lógica deste código, mas porque o módulo `sqlite3` da biblioteca padrão do Python não as inclui numa transacção implícita (não corre um `BEGIN` automático antes de DDL).

**Se isto for um comportamento intencional** (por exemplo, para forçar disciplina transaccional explícita em SQL livre), documenta-o de forma visível ao utilizador (já foi adicionado ao `DOC_USER.md`, secção 12). **Se não for intencional**, a correcção é simples: adicionar o mesmo padrão `if not engine_config["in_transaction"]: conn.commit()` dentro do loop de `handle_raw_sql`, depois de cada `cursor.execute(statement_stripped)` que não devolva `description` (ou seja, que não seja um `SELECT`).

---

## 7. Colisão de nomes entre macros e palavras-chave SQL

O *dispatcher* em `cli.py` decide entre macro e SQL bruto comparando apenas `parts[0].lower()` contra uma lista fixa de nomes reservados:

```
help, clear, cl, config, settings, configuration, conf,
.dbload, open, close, list, ls, print, inspect, audit,
.schema, export, update, rename, insert,
begin, commit, rollback, exit, quit
```

Como `insert` e `update` são também palavras-chave SQL padrão, qualquer instrução SQL bruta que comece literalmente por `INSERT` ou `UPDATE` **nunca chega a `sql_engine.py`** — é sempre capturada primeiro pela macro homónima, com os `parts` a serem interpretados segundo a sintaxe da macro (não da instrução SQL).

Isto foi confirmado empiricamente:

```
SS_SQL3 (sstable)> UPDATE sstable SET cliente='ZZZ' WHERE id=1;
Update record compilation collapsed: no such column: sstable
```

(`parts[1]` = `"sstable"` foi interpretado como o argumento `<coluna>` da macro `update`.)

**Duas formas de resolver isto, se decidires corrigir:**

a) **Verificação de intenção antes do dispatch** — em `cli.py`, antes de comparar `cmd` contra a lista de macros, verificar se a linha completa parece uma instrução SQL válida terminada em `;` ou reconhecida por `sqlite3.complete_statement()`, e nesse caso saltar directamente para `handle_raw_sql`, ignorando a macro homónima.

b) **Renomear as macros conflituosas** — por exemplo, `insert` → `add`, `update` → `set`/`upd`. Resolve a ambiguidade de raiz, mas é uma mudança que quebra compatibilidade com scripts/hábitos já existentes.

Enquanto isto não for resolvido, documenta-o claramente (já feito no `DOC_USER.md`, secção 11) para o utilizador saber contornar a limitação usando sempre a macro dedicada.

---

## 8. Parser multi-instrução do `sql_engine.py`

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

## 9. Exportação de dados — detalhes de implementação

- CSV e JSON usam apenas a biblioteca padrão (`csv`, `json`).
- PDF usa `reportlab.platypus` (`SimpleDocTemplate`, `Table`, `TableStyle`, `Paragraph`) — cada célula é envolvida num `Paragraph` (não texto simples), especificamente para obter quebra automática de linha em células longas.
- O `import` de `reportlab` está protegido por `try/except ImportError` no topo do módulo, com a flag `HAS_REPORTLAB` a controlar se `_export_pdf` sequer tenta correr. Isto permite que o resto do motor (CSV, JSON, todas as outras macros) funcione perfeitamente num ambiente onde `reportlab` nunca foi instalado.
- `handle_export_command` decide tabela-vs-query verificando se o payload, depois de `strip().upper()`, começa por `"SELECT"`. Isto significa que uma query começada por `WITH` (CTE) **não** é reconhecida como query livre — seria tratada como nome de tabela literal e falharia. Se precisares de exportar CTEs, terás de ajustar esta condição para também aceitar `"WITH"`.

---

## 10. `Makefile` e empacotamento com PyInstaller

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
- `make run` — assume `$(PY_MAIN)` (`src/cli.py`) tem permissão de execução (`chmod +x`) e usa `#!/usr/bin/env python3` como *shebang* (já presente no ficheiro).
- `make build` — empacota `src/cli.py` e todos os módulos que importa num único executável standalone via `PyInstaller`, colocado em `dist/ss_sqlite_cli`. Requer `pip install pyinstaller`. Como os módulos (`utils`, `config_commands`, etc.) são importados por nome directo (sem serem um pacote formal), o `PyInstaller` só os inclui correctamente se forem descobertos automaticamente a partir do mesmo directório de `cli.py` — se moveres ficheiros de sítio, volta a testar o `build` antes de assumir que continua a funcionar.
- `make fclean` — limpa artefactos de build (`build/`, `dist/`, `.spec`) e a base de dados de demonstração.
- `make re` — atalho para `fclean` seguido de `all`.

---

## 11. Limitações conhecidas e dívida técnica

| # | Limitação                                                                                       | Impacto                                                              | Ficheiro(s)          |
|---|----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|------------------------|
| 1 | SQL bruto começado por `INSERT`/`UPDATE` é capturado pelas macros homónimas (secção 7)                | Utilizador não consegue escrever `INSERT INTO`/`UPDATE` SQL puro directamente | `cli.py`                |
| 2 | `handle_raw_sql` nunca faz `conn.commit()` (secção 6)                                                    | `DELETE`/`INSERT`/`UPDATE` via SQL bruto exigem `commit` manual explícito       | `sql_engine.py`          |
| 3 | `handle_help_command()` não menciona `.dbload` nem `.schema`                                              | Utilizadores que só consultam `help` não descobrem estes dois comandos           | `config_commands.py`      |
| 4 | `handle_export_command` só reconhece `SELECT` como query livre, não `WITH` (CTE)                            | Exportar o resultado de uma CTE falha ou é mal interpretado como nome de tabela    | `export_commands.py`        |
| 5 | `handle_update_command` assume sempre `WHERE id = ?`                                                          | Tabelas sem coluna `id`, ou com chave primária de outro nome, não são suportadas     | `data_commands.py`            |
| 6 | Indentação mista (espaços + um tabulador) na linha do ramo `.schema` em `cli.py` (linha ~140)                    | Funciona por acaso (bloco de uma única linha, sem ambiguidade), mas é frágil e deve ser normalizada para só espaços | `cli.py`                        |
| 7 | `make all`/`make build` dependem de ferramentas externas (`sqlite3` CLI, `pyinstaller`) não verificadas antes de correr | Falha com erro genérico de shell (`command not found`) em vez de mensagem clara       | `Makefile`                        |

Nenhuma destas limitações foi corrigida automaticamente nesta revisão da documentação — ficam aqui registadas para decisão e priorização futura.

---

## 12. Sugestões de teste manual

Sequência mínima para validar uma alteração ao motor:

```bash
make re                       # regenerar database.db a partir de table_list.sql
python3 src/cli.py database.db
```

Dentro da shell:

```
help
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
.dbload :memory:
ls
exit
```

Confirma sempre, após qualquer alteração a `sql_engine.py` ou às macros de escrita, se as alterações **persistem** ao reabrir o mesmo ficheiro de base de dados numa nova invocação do processo — é a forma mais directa de apanhar regressões no comportamento de *commit* descrito na secção 6.
