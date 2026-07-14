# DOC_USER — Manual do Utilizador do SS_DB Engine

Este documento explica, em detalhe e com exemplos práticos, todos os comandos disponíveis na shell `SS_DB Engine`. Serve tanto para uma primeira utilização como para consulta pontual.

---

## Índice

1. [Arranque da shell](#1-arranque-da-shell)
2. [Conceitos-base: sessões, contexto de tabela e prompt](#2-conceitos-base-sessões-contexto-de-tabela-e-prompt)
3. [Comandos de gestão de sessões](#3-comandos-de-gestão-de-sessões)
4. [Comandos de navegação e ligação](#4-comandos-de-navegação-e-ligação)
5. [Comandos de leitura e inspecção](#5-comandos-de-leitura-e-inspecção)
6. [Comandos de escrita](#6-comandos-de-escrita)
7. [Exportação de dados](#7-exportação-de-dados)
8. [SQL bruto (raw SQL)](#8-sql-bruto-raw-sql)
9. [Transacções](#9-transacções)
10. [Telemetria e configuração (`config`)](#10-telemetria-e-configuração-config)
11. [Histórico de comandos](#11-histórico-de-comandos)
12. [Colisão entre macros e palavras-chave SQL](#12-colisão-entre-macros-e-palavras-chave-sql)
13. [Resolução de problemas frequentes](#13-resolução-de-problemas-frequentes)
14. [Referência rápida de todos os comandos](#14-referência-rápida-de-todos-os-comandos)

---

## 1. Arranque da shell

Há três formas de arrancar o motor:

```bash
# a) Via Makefile — gera database.db a partir de table_list.sql e arranca de imediato
make run

# b) Directamente com o interpretador, indicando um ficheiro de base de dados
#    (cria automaticamente uma sessão 'default' com esse ficheiro)
python3 src/cli.py database.db

# c) Sem argumentos — arranca em modo neutro, sem sessão activa
python3 src/cli.py
```

No modo sem argumentos, o motor fica à espera de um `connect` explícito. Usa `connect local :memory:` para uma base transitória em memória, ou `connect local ficheiro.db` para uma base persistente.

Ao entrar, a shell mostra um resumo do estado do motor e convida-te a escrever `help` ou `config`.

---

## 2. Conceitos-base: sessões, contexto de tabela e prompt

O motor opera sobre **sessões**. Cada sessão representa uma ligação activa a um motor de base de dados (SQLite, PostgreSQL, etc.), identificada por um **alias** curto.

O *prompt* reflecte sempre o estado completo da sessão activa:

| Prompt | Significado |
|---|---|
| `SS_DB>` | Sem sessão activa; usa `connect` para abrir uma |
| `SS_DB [sqlite::local]>` | Sessão SQLite activa com alias `local`, sem tabela aberta |
| `SS_DB [sqlite::local] (sstable)>` | Sessão activa, tabela `sstable` aberta com `open` |
| `SS_DB [postgres::prod]>` | Sessão PostgreSQL activa com alias `prod` |
| `SS_DB [sqlite::local] (sstable) [TX]>` | Sessão activa, tabela activa **e** transacção em curso |

Quando há uma tabela activa, comandos como `print`, `insert`, `update` e `list` actuam automaticamente sobre essa tabela, sem precisares de a nomear de novo.

---

## 3. Comandos de gestão de sessões

### `connect <alias> <connection_string>`

Regista e abre uma nova ligação à base de dados indicada, sob um alias à tua escolha. A primeira sessão registada torna-se automaticamente a sessão activa.

O tipo de motor é detectado automaticamente pelo prefixo da string de ligação:

| Prefixo | Motor |
|---|---|
| `postgresql://` ou `postgres://` | PostgreSQL (requer `psycopg2-binary`) |
| `mongodb://` | MongoDB (previsto; ainda não implementado) |
| Qualquer outro valor | SQLite (caminho de ficheiro ou `:memory:`) |

```
SS_DB> connect local database.db
Success: Registered connection [local] linked to sqlite://database.db

SS_DB [sqlite::local]> connect mem :memory:
Success: Registered connection [mem] linked to sqlite://:memory:

SS_DB [sqlite::local]> connect prod postgresql://user:pass@192.168.1.50/billing
Success: Registered connection [prod] linked to postgres://billing
```

### `use <alias>`

Muda o foco activo para a sessão indicada. O *prompt* actualiza-se de imediato.

```
SS_DB [sqlite::local]> use prod
Switched context to session [prod].
SS_DB [postgres::prod]>
```

### `sessions` / `connections`

Lista todas as sessões actualmente registadas, mostrando o tipo de motor, o nome da base de dados e a tabela activa (se houver). A sessão actualmente em foco é marcada com `[ACTIVE]`.

```
SS_DB [sqlite::local]> sessions

--- Active Sessions Registry ---
  [local] [ACTIVE] | Type: sqlite | DB: database.db | Table: sstable
  [prod]            | Type: postgres | DB: billing
  [mem]             | Type: sqlite | DB: :memory:
--------------------------------
```

### `disconnect <alias>`

Encerra e remove a sessão indicada do registo. Se era a sessão activa, o foco é transferido automaticamente para a seguinte sessão disponível.

```
SS_DB [sqlite::local]> disconnect mem
Active session removed. Focus shifted to [prod].
```

### `.dbload <ficheiro.db>`

Atalho de compatibilidade: fecha e substitui a sessão `default` (criada no arranque via argumento) por um novo ficheiro SQLite, sem reiniciar o processo.

```
SS_DB [sqlite::default]> .dbload outra_base.db
Successfully shifted database execution scope to: [outra_base.db]
```

Se a ligação ao novo ficheiro falhar, o motor recua automaticamente para uma base transitória em memória, para nunca ficar sem ligação activa.

---

## 4. Comandos de navegação e ligação

### `open <tabela>`

Fixa o contexto na tabela indicada. Falha com erro claro se a tabela não existir na sessão activa.

```
SS_DB [sqlite::local]> open sstable
SS_DB [sqlite::local] (sstable)>
```

### `close`

Sai do contexto de tabela activo, voltando à raiz da sessão. Emite um erro se já não houver tabela activa.

```
SS_DB [sqlite::local] (sstable)> close
SS_DB [sqlite::local]>
```

---

## 5. Comandos de leitura e inspecção

### `list` / `ls`

- Sem tabela activa: lista todas as tabelas/colecções da sessão activa.
- Com tabela activa: lista as colunas dessa tabela (nome, tipo, obrigatoriedade, valor por omissão, se é chave primária).
- `list <tabela>` a partir da raiz: lista as colunas dessa tabela específica, sem a "abrir".

```
SS_DB [sqlite::local]> list
Available Contexts (Tables/Views)
---------------------------------
sstable

SS_DB [sqlite::local]> open sstable
SS_DB [sqlite::local] (sstable)> list
cid  name         type     notnull  dflt_value  pk
---  -----------  -------  -------  ----------  --
0    id           INTEGER  0        NULL        1
1    cliente      TEXT     1        NULL        0
...
```

### `print`

- Sem tabela activa: lista as tabelas disponíveis (igual a `list`).
- Com tabela activa e sem argumentos: imprime **todas** as linhas e colunas da tabela.
- Com tabela activa e argumentos: imprime apenas as colunas indicadas.

```
SS_DB [sqlite::local] (sstable)> print
id  cliente  telefone   servico     tecnico  equipamento
--  -------  ---------  ----------  -------  -----------
1   Ana      900000000  Iluminação  Pedro    Lâmpada
...

SS_DB [sqlite::local] (sstable)> print cliente telefone
cliente  telefone
-------  ---------
Ana      900000000
...
```

### `inspect` / `audit [<tabela>]`

Audita metadados estruturais da tabela activa (ou da tabela indicada): índices definidos e chaves estrangeiras.

```
SS_DB [sqlite::local] (sstable)> inspect
=== Deep Architectural Inspection Profile: [sstable] ===
  Indexes     : No database indexes mapped to this entity.
  Foreign Keys: No external foreign constraints discovered.
==================================================================
```

### `.schema [<tabela>]`

Extrai e mostra a instrução DDL original (`CREATE TABLE ...`) usada para criar a tabela activa ou indicada. Útil para copiar rapidamente a definição exacta de uma tabela.

```
SS_DB [sqlite::local] (sstable)> .schema
CREATE TABLE sstable
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente TEXT NOT NULL,
    ...
);
```

---

## 6. Comandos de escrita

### `update <coluna> <id> <novo_valor>`

Actualiza uma única coluna, numa única linha, identificada pelo valor da coluna `id`, dentro da tabela activa. **Requer contexto de tabela aberto.**

```
SS_DB [sqlite::local] (sstable)> update cliente 1 Mariana
Success: Table 'sstable' column 'cliente' updated for ID 1.
```

> Se não estiveres dentro de uma transacção explícita, a alteração é gravada em disco de imediato (auto-commit).

### `rename`

Comportamento adaptável consoante o contexto:

| Contexto | Sintaxe | Efeito |
|---|---|---|
| Tabela activa | `rename <novo_nome_tabela>` | Renomeia a tabela activa |
| Tabela activa | `rename <coluna_antiga> <coluna_nova>` | Renomeia uma coluna da tabela activa |
| Raiz (sem tabela) | `rename <tabela_antiga> <tabela_nova>` | Renomeia a tabela indicada |
| Raiz (sem tabela) | `rename <tabela> <coluna_antiga> <coluna_nova>` | Renomeia uma coluna de uma tabela específica |

```
SS_DB [sqlite::local] (sstable)> rename clientes_tabela
Table 'sstable' successfully renamed to 'clientes_tabela'.
```

### `insert <valor1> <valor2> ... <valorN>`

Insere uma nova linha na tabela activa. **Requer contexto de tabela aberto.** A shell calcula automaticamente quantos e quais campos preencher, ignorando colunas de chave primária auto-incrementada — por isso o número de valores dados deve corresponder exactamente ao número de colunas *não* auto-incrementadas.

```
SS_DB [sqlite::local] (sstable)> insert "Zeca" 900000002 "Som" "Ana" "Cabo"
Row successfully inserted into 'sstable'.
```

Regras de conversão de tipo:
- O texto literal `NULL` (em qualquer capitalização) é convertido para `NULL` na base de dados.
- Sequências só de dígitos são convertidas para inteiro.
- Tudo o resto é tratado como texto.
- Usa aspas simples ou duplas para valores com espaços.

---

## 7. Exportação de dados

```
export <csv|json|pdf> <ficheiro_destino> <tabela_ou_SELECT>
```

O terceiro argumento pode ser:
- O **nome de uma tabela** — exporta todas as linhas e colunas dessa tabela.
- Uma **instrução `SELECT` completa** — exporta apenas o resultado dessa *query*.

A extensão do ficheiro é adicionada automaticamente se não a indicares.

```
SS_DB [sqlite::local]> export csv relatorio sstable
Success: 5 rows exported natively into CSV format -> [relatorio.csv]

SS_DB [sqlite::local]> export json clientes_ana "SELECT * FROM sstable WHERE cliente = 'Ana'"
Success: 3 rows exported natively into JSON format -> [clientes_ana.json]

SS_DB [sqlite::local]> export pdf relatorio_completo sstable
Success: 5 rows exported natively into PDF format -> [relatorio_completo.pdf]
```

A exportação para PDF produz um documento A4, com cabeçalho destacado, quebra automática de texto por célula e faixas alternadas de cor para facilitar a leitura de tabelas longas. **Requer o pacote `reportlab` instalado** — caso contrário, a shell avisa e sugere o comando de instalação.

---

## 8. SQL bruto (*raw SQL*)

Qualquer entrada que não corresponda a um dos comandos/macros reservados é interpretada como **SQL puro** e enviada directamente ao motor activo.

```
SS_DB [sqlite::local]> SELECT cliente, COUNT(*) FROM sstable GROUP BY cliente;
cliente  COUNT(*)
-------  --------
Ana      3
João     2
```

### Múltiplas instruções numa só linha

O motor separa correctamente várias instruções SQL escritas na mesma linha e terminadas por `;`, mesmo que existam pontos-e-vírgulas dentro de literais de texto:

```
SS_DB [sqlite::local]> SELECT * FROM sstable WHERE id=1; SELECT * FROM sstable WHERE id=2;
```

Cada instrução é executada e o seu resultado (se aplicável) impresso sequencialmente.

> **Atenção:** consulta a secção 12 sobre colisões de nomes antes de usares `INSERT`/`UPDATE` em SQL bruto.

---

## 9. Transacções

```
SS_DB [sqlite::local]> begin
Transaction started. Structural locks are now active.

SS_DB [sqlite::local] [TX]> update cliente 1 "Mariana"
SS_DB [sqlite::local] [TX]> update cliente 2 "Mariana"

SS_DB [sqlite::local] [TX]> commit
Transaction successfully committed to disk storage.
```

- `begin` — inicia um bloco transaccional explícito. Enquanto activo, os comandos `update`, `insert` e `rename` **não** gravam automaticamente em disco a cada operação — ficam à espera do `commit`.
- `commit` — grava permanentemente todas as alterações acumuladas desde o `begin`.
- `rollback` — descarta todas as alterações acumuladas desde o `begin`, revertendo ao estado anterior.

Tentar `commit` ou `rollback` sem uma transacção activa apenas emite um aviso, sem efeito.

> **Nota:** mudar de sessão com `use` enquanto uma transacção está activa não faz rollback automático na sessão anterior. Confirma ou cancela sempre a transacção antes de mudar de foco.

---

## 10. Telemetria e configuração (`config`)

```
SS_DB [sqlite::local]> config
--- SSSQLite Engine Configuration Status [database.db] ---
  echo   (Statement Echoing)       : OFF
  timer  (Execution Profiler)      : OFF
  eqp    (Explain Query Plan)      : OFF
  stats  (Low-Level DB Telemetry)  : OFF
  [Disk Weight/Allocation]         : 4.00 KB
-----------------------------------------------------------------
```

Alterna cada opção com `config <opção> on|off` (aceita também `true`/`false` e `1`/`0`):

| Opção | Efeito quando activa |
|---|---|
| `echo` | Ecoa literalmente cada linha de *input* recebida, antes de a executar |
| `timer` | Mostra o tempo de execução (em segundos, precisão de microssegundos) de cada instrução |
| `eqp` | Antes de cada `SELECT`/`WITH`, mostra o plano de execução (`EXPLAIN QUERY PLAN`) |
| `stats` | Após cada instrução, mostra contagem de páginas, tamanho de página, páginas livres e peso em disco |

```
SS_DB [sqlite::local]> config timer on
Configuration option 'timer' successfully enabled.
```

Os alias `settings` e `conf` são equivalentes a `config`.

---

## 11. Histórico de comandos

A shell grava automaticamente todo o histórico de comandos escritos em `~/.ss_sqlite_history`, através do módulo `readline`. Isto permite:

- Navegar pelo histórico entre sessões com as setas ↑ / ↓.
- Pesquisa incremental no histórico (normalmente `Ctrl+R`, dependendo da configuração do teu terminal).

O ficheiro de histórico é gravado automaticamente ao sair da shell (`exit`, `quit`, `Ctrl+D` ou `Ctrl+C`).

---

## 12. Colisão entre macros e palavras-chave SQL

A shell decide se uma linha escrita é uma **macro interna** ou **SQL bruto** olhando apenas para a primeira palavra. Isto significa que, se escreveres uma instrução SQL cuja primeira palavra coincide com o nome de uma macro, a shell **não** a trata como SQL — trata-a como a macro correspondente.

As macros afectadas são: `connect`, `use`, `sessions`, `disconnect`, `open`, `close`, `list`, `print`, `inspect`, `audit`, `export`, `update`, `rename`, `insert`, `begin`, `commit`, `rollback`, `help`, `clear`, `cl`, `config`, `settings`, `conf`.

Na prática, isto afecta sobretudo `INSERT` e `UPDATE`, por serem também palavras-chave SQL muito comuns:

```
SS_DB [sqlite::local] (sstable)> INSERT INTO sstable(cliente, telefone, servico, tecnico, equipamento)
                    VALUES ('Rita', 900000003, 'Som', 'Ana', 'Cabo');
```

Esta linha **não** executa como SQL — a shell tenta interpretá-la como a macro `insert`, e falha ou produz um resultado inesperado, porque os argumentos não correspondem à sintaxe da macro.

**Como contornar:**
- Usa sempre a macro `insert <valores...>` para inserir linhas (ver secção 6), em vez de escreveres `INSERT INTO ...` directamente.
- Para `UPDATE`, usa a macro `update <coluna> <id> <novo_valor>` (secção 6) sempre que a actualização for simples (uma coluna, uma linha, identificada por `id`).
- Para actualizações mais complexas (múltiplas colunas, condições `WHERE` compostas, sub-*queries*), que a macro `update` não cobre, terás de recorrer a ferramentas externas (por exemplo, o `sqlite3` CLI oficial) até essa limitação ser resolvida no motor.

---

## 13. Resolução de problemas frequentes

**"Error: No active database session."**
Não há sessão activa. Usa `connect <alias> <connection_string>` para abrir uma.

**"Error: The 'psycopg2' package is not installed in the active environment."**
Instala o *driver* com `python3 -m pip install --user psycopg2-binary` e tenta novamente o `connect postgresql://...`.

**"Error: The 'reportlab' dependency is missing from the active environment."**
Instala o pacote com `python3 -m pip install --user reportlab` e tenta novamente o `export pdf`.

**Uma instrução `INSERT`/`UPDATE` escrita directamente parece "não fazer nada" ou dá erro estranho.**
Consulta a secção 12 — provavelmente colidiu com a macro homónima. Usa a macro dedicada (`insert`/`update`) em vez de SQL bruto.

**Uma instrução SQL bruta (`DELETE`, `INSERT` sem colisão, etc.) parece executar sem erro, mas ao reabrir a base de dados a alteração desapareceu.**
As instruções SQL enviadas directamente ao motor (fora das macros dedicadas) **não são gravadas automaticamente em disco** — precisas de escrever `commit` a seguir para confirmares a alteração, mesmo fora de um bloco `begin` explícito. As macros `update`, `insert` e `rename` já fazem esse `commit` automaticamente por ti (excepto dentro de um bloco `begin` activo, caso em que aguardam o teu `commit`/`rollback`).

**`export csv/json/pdf` diz "did not output any structured database fields".**
A tabela ou `SELECT` indicado não devolveu colunas — confirma o nome da tabela ou a sintaxe da *query*.

**A shell abriu sem sessão activa e não consigo usar `open` nem `print`.**
Arrancaste o script sem indicar um ficheiro de base de dados, ou nenhum `connect` foi ainda executado. Usa `connect local database.db` dentro da sessão, ou reinicia indicando o ficheiro: `python3 src/cli.py <ficheiro.db>`.

---

## 14. Referência rápida de todos os comandos

### Gestão de sessões

| Comando | Descrição |
|---|---|
| `connect <alias> <conn_string>` | Regista e abre uma nova sessão (SQLite, PostgreSQL, etc.) |
| `use <alias>` | Muda o foco activo para a sessão indicada |
| `sessions` / `connections` | Lista todas as sessões registadas e o seu estado |
| `disconnect <alias>` | Encerra e remove a sessão indicada |
| `.dbload <ficheiro.db>` | Atalho: substitui a sessão `default` pelo ficheiro indicado |

### Navegação e inspecção

| Comando | Descrição |
|---|---|
| `open <tabela>` | Abre/fixa o contexto numa tabela |
| `close` | Fecha o contexto de tabela activo |
| `list` / `ls [tabela]` | Lista tabelas (raiz) ou colunas (tabela activa/indicada) |
| `print [colunas...]` | Lista tabelas (raiz) ou imprime linhas/colunas (tabela activa) |
| `inspect` / `audit [tabela]` | Audita índices e chaves estrangeiras |
| `.schema [tabela]` | Mostra a instrução DDL (`CREATE TABLE`) original |

### Escrita e exportação

| Comando | Descrição |
|---|---|
| `insert <valores...>` | Insere uma nova linha na tabela activa |
| `update <coluna> <id> <valor>` | Actualiza um valor numa linha, por `id` |
| `rename ...` | Renomeia tabelas ou colunas (sintaxe varia com o contexto — ver secção 6) |
| `export <csv\|json\|pdf> <ficheiro> <tabela\|SELECT>` | Exporta dados para ficheiro externo |

### Transacções e controlo

| Comando | Descrição |
|---|---|
| `begin` | Inicia uma transacção explícita |
| `commit` | Confirma e grava a transacção em curso |
| `rollback` | Descarta a transacção em curso |
| `config` / `settings` / `conf` | Mostra métricas da base de dados e estado da telemetria |
| `config <opção> on\|off` | Activa/desactiva `echo`, `timer`, `eqp` ou `stats` |
| `help` | Mostra o menu de ajuda |
| `clear` / `cl` | Limpa o ecrã do terminal |
| `exit` / `quit` | Termina a shell e fecha todas as sessões |
| *qualquer outra entrada* | Executada como SQL bruto (ver secções 8 e 12) |
