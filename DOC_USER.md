# DOC_USER — Manual do Utilizador do SS_SQLite

Este documento explica, em detalhe e com exemplos práticos, todos os comandos disponíveis na shell `SS_SQLite`. Serve tanto para uma primeira utilização como para consulta pontual.

---

## Índice

1. [Arranque da shell](#1-arranque-da-shell)
2. [Conceitos-base: contexto de tabela e prompt](#2-conceitos-base-contexto-de-tabela-e-prompt)
3. [Comandos de navegação e ligação](#3-comandos-de-navegação-e-ligação)
4. [Comandos de leitura e inspecção](#4-comandos-de-leitura-e-inspecção)
5. [Comandos de escrita](#5-comandos-de-escrita)
6. [Exportação de dados](#6-exportação-de-dados)
7. [SQL bruto (raw SQL)](#7-sql-bruto-raw-sql)
8. [Transacções](#8-transacções)
9. [Telemetria e configuração (`config`)](#9-telemetria-e-configuração-config)
10. [Histórico de comandos](#10-histórico-de-comandos)
11. [Colisão entre macros e palavras-chave SQL](#11-colisão-entre-macros-e-palavras-chave-sql)
12. [Resolução de problemas frequentes](#12-resolução-de-problemas-frequentes)
13. [Referência rápida de todos os comandos](#13-referência-rápida-de-todos-os-comandos)

---

## 1. Arranque da shell

Há três formas de arrancar o motor:

```bash
# a) Via Makefile — gera database.db a partir de table_list.sql e arranca de imediato
make run

# b) Directamente com o interpretador, indicando um ficheiro de base de dados
python3 src/cli.py database.db

# c) Sem argumentos — abre uma base de dados transitória em memória (:memory:)
python3 src/cli.py
```

No modo `:memory:`, tudo o que crias e insere desaparece assim que a shell fecha, a não ser que ligues uma base persistente a meio da sessão com `.dbload` (ver secção 3).

Ao entrar, a shell mostra um resumo do estado do motor e convida-te a escrever `help` ou `config`.

---

## 2. Conceitos-base: contexto de tabela e prompt

O prompt muda consoante o estado interno da shell:

| Prompt                              | Significado                                         |
|--------------------------------------|------------------------------------------------------|
| `SS_SQL3>`                            | Sem tabela activa (contexto de raiz)                  |
| `SS_SQL3 (nome_tabela)>`               | Tabela `nome_tabela` activa (aberta com `open`)         |
| `SS_SQL3 [TX ACTIVE]>`                  | Transacção explícita em curso (`begin` já foi executado) |
| `SS_SQL3 (nome_tabela) [TX ACTIVE]>`     | Tabela activa **e** transacção em curso                  |

Quando há uma tabela activa, comandos como `print`, `insert`, `update` e `list` actuam automaticamente sobre essa tabela, sem precisares de a nomear de novo.

---

## 3. Comandos de navegação e ligação

### `open <tabela>`
Fixa o contexto na tabela indicada. Falha com erro claro se a tabela não existir.

```
SS_SQL3> open sstable
SS_SQL3 (sstable)>
```

### `close`
Sai do contexto de tabela activo, voltando à raiz. Emite um erro se já não houver tabela activa.

```
SS_SQL3 (sstable)> close
SS_SQL3>
```

### `.dbload <ficheiro.db>`
Fecha a ligação à base de dados actual e liga a shell a um **novo ficheiro**, sem reiniciar o processo. Qualquer tabela activa e qualquer transacção em curso são limpas automaticamente ao mudar de base.

```
SS_SQL3> .dbload outra_base.db
Successfully shifted database execution scope to: [outra_base.db]
```

Se a ligação ao novo ficheiro falhar (por exemplo, caminho inválido ou permissões insuficientes), a shell recua automaticamente para uma base transitória em memória, para nunca ficar sem ligação activa.

> **Nota:** Este comando começa por ponto (`.`), à semelhança dos meta-comandos do `sqlite3` CLI oficial (`.tables`, `.schema`, etc.).

---

## 4. Comandos de leitura e inspecção

### `list` / `ls`
- Sem tabela activa: lista todas as tabelas da base de dados.
- Com tabela activa: lista as colunas dessa tabela (nome, tipo, obrigatoriedade, valor por omissão, se é chave primária).
- `list <tabela>` a partir da raiz: lista as colunas dessa tabela específica, sem a "abrir".

```
SS_SQL3> list
Available Tables Context
------------------------
sstable

SS_SQL3> open sstable
SS_SQL3 (sstable)> list
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
SS_SQL3 (sstable)> print
id  cliente  telefone   servico     tecnico  equipamento
--  -------  ---------  ----------  -------  -----------
1   Ana      900000000  Iluminação  Pedro    Lâmpada
...

SS_SQL3 (sstable)> print cliente telefone
cliente  telefone
-------  ---------
Ana      900000000
...
```

### `inspect` / `audit [<tabela>]`
Audita metadados estruturais "escondidos" da tabela activa (ou da tabela indicada): índices definidos e chaves estrangeiras.

```
SS_SQL3 (sstable)> inspect
=== Deep Architectural Inspection Profile: [sstable] ===
  Indexes     : No database indexes mapped to this entity.
  Foreign Keys: No external foreign constraints discovered.
==================================================================
```

### `.schema [<tabela>]`
Extrai e mostra a instrução DDL original (`CREATE TABLE ...`) usada para criar a tabela activa ou indicada. Útil para copiar rapidamente a definição exacta de uma tabela.

```
SS_SQL3 (sstable)> .schema
CREATE TABLE sstable
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente TEXT NOT NULL,
    ...
);
```

---

## 5. Comandos de escrita

### `update <coluna> <id> <novo_valor>`
Actualiza uma única coluna, numa única linha, identificada pelo valor da coluna `id`, dentro da tabela activa. **Requer contexto de tabela aberto.**

```
SS_SQL3 (sstable)> update cliente 1 Mariana
Success: Table 'sstable' column 'cliente' updated for ID 1.
```

> Se não estiveres dentro de uma transacção explícita, a alteração é gravada em disco de imediato (auto-commit).

### `rename`
Comportamento adaptável consoante o contexto:

| Contexto        | Sintaxe                                     | Efeito                              |
|------------------|-----------------------------------------------|----------------------------------------|
| Tabela activa    | `rename <novo_nome_tabela>`                     | Renomeia a tabela activa                 |
| Tabela activa    | `rename <coluna_antiga> <coluna_nova>`            | Renomeia uma coluna da tabela activa       |
| Raiz (sem tabela) | `rename <tabela_antiga> <tabela_nova>`             | Renomeia a tabela indicada                  |
| Raiz (sem tabela) | `rename <tabela> <coluna_antiga> <coluna_nova>`     | Renomeia uma coluna de uma tabela específica |

```
SS_SQL3 (sstable)> rename clientes_tabela
Table 'sstable' successfully renamed to 'clientes_tabela'.
```

### `insert <valor1> <valor2> ... <valorN>`
Insere uma nova linha na tabela activa. **Requer contexto de tabela aberto.** A shell calcula automaticamente quantos e quais campos preencher, ignorando colunas de chave primária auto-incrementada — por isso o número de valores dados deve corresponder exactamente ao número de colunas *não* auto-incrementadas.

```
SS_SQL3 (sstable)> insert "Zeca" 900000002 "Som" "Ana" "Cabo"
Row successfully inserted into 'sstable'.
```

Regras de conversão de tipo:
- O texto literal `NULL` (em qualquer capitalização) é convertido para `NULL` na base de dados.
- Sequências só de dígitos são convertidas para inteiro.
- Tudo o resto é tratado como texto.
- Usa aspas simples ou duplas para valores com espaços.

---

## 6. Exportação de dados

```
export <csv|json|pdf> <ficheiro_destino> <tabela_ou_SELECT>
```

O terceiro argumento pode ser:
- O **nome de uma tabela** — exporta todas as linhas e colunas dessa tabela.
- Uma **instrução `SELECT` completa** — exporta apenas o resultado dessa query.

A extensão do ficheiro é adicionada automaticamente se não a indicares.

```
SS_SQL3> export csv relatorio sstable
Success: 5 rows exported natively into CSV format -> [relatorio.csv]

SS_SQL3> export json clientes_ana "SELECT * FROM sstable WHERE cliente = 'Ana'"
Success: 3 rows exported natively into JSON format -> [clientes_ana.json]

SS_SQL3> export pdf relatorio_completo sstable
Success: 5 rows exported natively into PDF format -> [relatorio_completo.pdf]
```

A exportação para PDF produz um documento A4, com cabeçalho destacado, quebra automática de texto por célula e faixas alternadas de cor para facilitar a leitura de tabelas longas. **Requer o pacote `reportlab` instalado** — caso contrário, a shell avisa e sugere o comando de instalação.

---

## 7. SQL bruto (*raw SQL*)

Qualquer entrada que não corresponda a um dos comandos/macros reservados é interpretada como **SQL puro** e enviada directamente ao motor SQLite.

```
SS_SQL3> SELECT cliente, COUNT(*) FROM sstable GROUP BY cliente;
cliente  COUNT(*)
-------  --------
Ana      3
João     2
```

### Múltiplas instruções numa só linha
O motor separa correctamente várias instruções SQL escritas na mesma linha e terminadas por `;`, mesmo que existam pontos-e-vírgulas dentro de literais de texto:

```
SS_SQL3> SELECT * FROM sstable WHERE id=1; SELECT * FROM sstable WHERE id=2;
```

Cada instrução é executada e o seu resultado (se aplicável) impresso sequencialmente.

> **Atenção:** consulta a secção 11 sobre colisões de nomes antes de usares `INSERT`/`UPDATE` em SQL bruto.

---

## 8. Transacções

```
SS_SQL3> begin
Transaction started. Structural locks are now active.

SS_SQL3 [TX ACTIVE]> update cliente 1 "Mariana"
SS_SQL3 [TX ACTIVE]> update cliente 2 "Mariana"

SS_SQL3 [TX ACTIVE]> commit
Transaction successfully committed to disk storage.
```

- `begin` — inicia um bloco transaccional explícito. Enquanto activo, os comandos `update`, `insert` e `rename` **não** gravam automaticamente em disco a cada operação — ficam à espera do `commit`.
- `commit` — grava permanentemente todas as alterações acumuladas desde o `begin`.
- `rollback` — descarta todas as alterações acumuladas desde o `begin`, revertendo ao estado anterior.

Tentar `commit` ou `rollback` sem uma transacção activa apenas emite um aviso, sem efeito.

---

## 9. Telemetria e configuração (`config`)

```
SS_SQL3> config
--- SSSQLite Engine Configuration Status [database.db] ---
  echo   (Statement Echoing)       : OFF
  timer  (Execution Profiler)      : OFF
  eqp    (Explain Query Plan)      : OFF
  stats  (Low-Level DB Telemetry)  : OFF
  [Disk Weight/Allocation]         : 4.00 KB
-----------------------------------------------------------------
```

Alterna cada opção com `config <opção> on|off` (aceita também `true`/`false` e `1`/`0`):

| Opção   | Efeito quando activa                                                                 |
|----------|-----------------------------------------------------------------------------------------|
| `echo`    | Ecoa literalmente cada linha de *input* recebida, antes de a executar                     |
| `timer`   | Mostra o tempo de execução (em segundos, precisão de microssegundos) de cada instrução      |
| `eqp`     | Antes de cada `SELECT`/`WITH`, mostra o plano de execução (`EXPLAIN QUERY PLAN`)              |
| `stats`   | Após cada instrução, mostra contagem de páginas, tamanho de página, páginas livres e peso em disco |

```
SS_SQL3> config timer on
Configuration option 'timer' successfully enabled.
```

Os alias `settings` e `conf` são equivalentes a `config`.

---

## 10. Histórico de comandos

A shell grava automaticamente todo o histórico de comandos escritos em `~/.ss_sqlite_history`, através do módulo `readline`. Isto permite:

- Navegar pelo histórico entre sessões com as setas ↑ / ↓.
- Pesquisa incremental no histórico (normalmente `Ctrl+R`, dependendo da configuração do teu terminal).

O ficheiro de histórico é gravado automaticamente ao sair da shell (`exit`, `quit`, `Ctrl+D` ou `Ctrl+C`).

---

## 11. Colisão entre macros e palavras-chave SQL

A shell decide se uma linha escrita é uma **macro interna** ou **SQL bruto** olhando apenas para a primeira palavra. Isto significa que, se escreveres uma instrução SQL cuja primeira palavra coincide com o nome de uma macro, a shell **não** a trata como SQL — trata-a como a macro correspondente.

As macros afectadas são: `open`, `close`, `list`, `print`, `inspect`, `audit`, `export`, `update`, `rename`, `insert`, `begin`, `commit`, `rollback`, `help`, `clear`, `cl`, `config`, `settings`, `conf`.

Na prática, isto afecta sobretudo `INSERT` e `UPDATE`, por serem também palavras-chave SQL muito comuns:

```
SS_SQL3 (sstable)> INSERT INTO sstable(cliente, telefone, servico, tecnico, equipamento)
                    VALUES ('Rita', 900000003, 'Som', 'Ana', 'Cabo');
```

Esta linha **não** executa como SQL — a shell tenta interpretá-la como a macro `insert`, e falha ou produz um resultado inesperado, porque os argumentos não correspondem à sintaxe da macro.

**Como contornar:**
- Usa sempre a macro `insert <valores...>` para inserir linhas (ver secção 5), em vez de escreveres `INSERT INTO ...` directamente.
- Para `UPDATE`, usa a macro `update <coluna> <id> <novo_valor>` (secção 5) sempre que a actualização for simples (uma coluna, uma linha, identificada por `id`).
- Para actualizações mais complexas (múltiplas colunas, condições `WHERE` compostas, sub-queries), que a macro `update` não cobre, terás de recorrer a ferramentas externas (por exemplo, o `sqlite3` CLI oficial) até essa limitação ser resolvida no motor.

---

## 12. Resolução de problemas frequentes

**"Error: The 'reportlab' dependency is missing from the active environment."**
Instala o pacote com `python3 -m pip install --user reportlab` e tenta novamente o `export pdf`.

**Uma instrução `INSERT`/`UPDATE` escrita directamente parece "não fazer nada" ou dá erro estranho.**
Consulta a secção 11 — provavelmente colidiu com a macro homónima. Usa a macro dedicada (`insert`/`update`) em vez de SQL bruto.

**Uma instrução SQL bruta (`DELETE`, `INSERT` sem colisão, etc.) parece executar sem erro, mas ao reabrir a base de dados a alteração desapareceu.**
As instruções SQL enviadas directamente ao motor (fora das macros dedicadas) **não são gravadas automaticamente em disco** — precisas de escrever `commit` a seguir para confirmares a alteração, mesmo fora de um bloco `begin` explícito. As macros `update`, `insert` e `rename` já fazem esse `commit` automaticamente por ti (excepto dentro de um bloco `begin` activo, caso em que aguardam o teu `commit`/`rollback`).

**`export csv/json/pdf` diz "did not output any structured database fields".**
A tabela ou `SELECT` indicado não devolveu colunas — confirma o nome da tabela ou a sintaxe da query.

**A shell abriu em modo `:memory:` sem eu querer.**
Arrancaste o script sem indicar um ficheiro de base de dados. Usa `.dbload <ficheiro.db>` dentro da sessão, ou reinicia indicando o ficheiro: `python3 src/cli.py <ficheiro.db>`.

---

## 13. Referência rápida de todos os comandos

| Comando                                    | Descrição                                                              |
|----------------------------------------------|----------------------------------------------------------------------------|
| `help`                                          | Mostra o menu de ajuda                                                       |
| `clear` / `cl`                                    | Limpa o ecrã do terminal                                                       |
| `config` / `settings` / `conf`                      | Mostra métricas da base de dados e estado da telemetria                         |
| `config <opção> on\|off`                              | Activa/desactiva `echo`, `timer`, `eqp` ou `stats`                                |
| `.dbload <ficheiro.db>`                                 | Muda a base de dados activa em tempo real                                          |
| `open <tabela>`                                          | Abre/fixa o contexto numa tabela                                                     |
| `close`                                                   | Fecha o contexto de tabela activo                                                     |
| `list` / `ls` `[tabela]`                                    | Lista tabelas (raiz) ou colunas (tabela activa/indicada)                                |
| `print [colunas...]`                                          | Lista tabelas (raiz) ou imprime linhas/colunas (tabela activa)                            |
| `inspect` / `audit [tabela]`                                    | Audita índices e chaves estrangeiras                                                        |
| `.schema [tabela]`                                                | Mostra a instrução DDL (`CREATE TABLE`) original                                              |
| `export <csv\|json\|pdf> <ficheiro> <tabela\|SELECT>`               | Exporta dados para ficheiro externo                                                             |
| `update <coluna> <id> <valor>`                                        | Actualiza um valor numa linha, por `id`                                                          |
| `rename ...`                                                            | Renomeia tabelas ou colunas (sintaxe varia com o contexto — ver secção 5)                          |
| `insert <valores...>`                                                     | Insere uma nova linha na tabela activa                                                              |
| `begin`                                                                     | Inicia uma transacção explícita                                                                       |
| `commit`                                                                      | Confirma e grava a transacção em curso                                                                  |
| `rollback`                                                                      | Descarta a transacção em curso                                                                            |
| `exit` / `quit`                                                                   | Termina a shell                                                                                             |
| *qualquer outra entrada*                                                            | Executada como SQL bruto (ver secção 7 e 11)                                                                  |
