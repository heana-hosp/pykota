# Documentação Completa do Sistema PyKota

## Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Componentes Principais](#componentes-principais)
4. [Métodos de Contagem de Páginas](#métodos-de-contagem-de-páginas)
5. [Sistema de Armazenamento](#sistema-de-armazenamento)
6. [Ferramentas de Linha de Comando](#ferramentas-de-linha-de-comando)
7. [Backend CUPS](#backend-cups)
8. [Sistema de Configuração](#sistema-de-configuração)
9. [Sistema de Relatórios](#sistema-de-relatórios)
10. [Funcionalidades Avançadas](#funcionalidades-avançadas)

---

## Visão Geral

PyKota é um sistema completo de controle de cotas e contabilização de impressão para CUPS (Common Unix Printing System) e LPRng. O sistema permite:

- **Controle de Cotas**: Limitar o número de páginas que usuários podem imprimir
- **Contabilização**: Rastrear todas as impressões realizadas
- **Cobrança**: Associar custos por página ou por job
- **Relatórios**: Gerar relatórios detalhados de uso
- **Políticas Flexíveis**: Configurar diferentes políticas por impressora

### Projetos que Compõem o PyKota

1. **pykota**: Sistema principal de cotas
2. **pkpgcounter**: Parser de Page Description Languages (PDL)
3. **pkipplib**: Biblioteca Python para IPP e CUPS
4. **pykoticon**: Cliente Windows para notificações
5. **tea4cups**: (Não migrado para Python 3)

---

## Arquitetura do Sistema

### Fluxo de Processamento de Impressão

```
Cliente → CUPS → cupspykota (backend) → PyKota Filter → Impressora Real
                ↓
         Verificação de Cotas
         Contabilização
         Atualização de Banco de Dados
```

### Componentes de Software

```
┌─────────────────────────────────────────────────────────┐
│                    CUPS Server                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │         cupspykota (Backend)                     │   │
│  │  - Intercepta jobs de impressão                  │   │
│  │  - Gerencia ciclo de vida do job                 │   │
│  │  - Chama filtros PyKota                          │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│              PyKota Filter (kotafilter)                │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Pre-Accounter (opcional)                        │   │
│  │  - Calcula tamanho do job antes da impressão     │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Verificação de Cotas                           │   │
│  │  - Verifica saldo/limite do usuário             │   │
│  │  - Verifica cotas de grupos                     │   │
│  │  - Aplica políticas (ALLOW/DENY/EXTERNAL)       │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Accounter (pós-impressão)                      │   │
│  │  - Contabiliza páginas impressas                │   │
│  │  - Atualiza banco de dados                      │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│              Backend Real da Impressora                 │
│  (socket://, ipp://, usb://, etc)                      │
└─────────────────────────────────────────────────────────┘
```

---

## Componentes Principais

### 1. PyKota Core (`pykota/src/pykota/`)

#### 1.1. Sistema de Armazenamento (`storage.py`)

Abstração de banco de dados que suporta múltiplos backends:

- **PostgreSQL** (`pgstorage.py`)
- **MySQL** (`mysqlstorage.py`)
- **SQLite** (`sqlitestorage.py`)
- **LDAP** (`ldapstorage.py`)

**Entidades Principais:**

- `StorageUser`: Usuários do sistema
- `StorageGroup`: Grupos de usuários
- `StoragePrinter`: Impressoras
- `StorageUserPQuota`: Cotas de usuário por impressora
- `StorageGroupPQuota`: Cotas de grupo por impressora
- `StorageJob`: Histórico de jobs de impressão
- `StorageBillingCode`: Códigos de faturamento

**Funcionalidades:**

- Cache de objetos para performance
- Transações de banco de dados
- Lazy loading de relacionamentos
- Suporte a hierarquia de impressoras (grupos)

#### 1.2. Sistema de Contagem (`accounter.py` + `accounters/`)

Três métodos principais de contagem:

**a) Software Accounting (`accounters/software.py`)**
- Usa parser PDL interno (pkpgcounter) ou script externo
- Analisa o arquivo de impressão antes/depois
- Suporta múltiplos formatos: PostScript, PDF, PCL, etc.

**b) Hardware Accounting (`accounters/hardware.py`)**
- Consulta contador interno da impressora
- Métodos: SNMP, PJL, Netatalk
- Lê contador antes e depois do job
- Diferença = número de páginas

**c) Ink Accounting (`accounters/ink.py`)**
- Calcula cobertura de tinta por página
- Suporta espaços de cor: CMYK, CMY, RGB, BW, GC
- Aplica coeficientes por cor
- Custo baseado em porcentagem de cobertura

#### 1.3. Sistema de Configuração (`config.py`)

Gerencia arquivos de configuração:

- `pykota.conf`: Configuração principal
- `pykotadmin.conf`: Configuração administrativa (senhas)

**Seções de Configuração:**

- `[global]`: Configurações globais
- `[printer_name]`: Configurações por impressora

**Principais Opções:**

- `storagebackend`: Backend de banco (postgresql, mysql, sqlite, ldap)
- `accounter`: Método de contagem (software, hardware, ink)
- `preaccounter`: Pré-contagem (opcional)
- `policy`: Política padrão (ALLOW, DENY, EXTERNAL)
- `enforcement`: Modo de aplicação (STRICT, LAXIST)
- `mailto`: Destinatários de emails (USER, ADMIN, BOTH, EXTERNAL)
- `gracedelay`: Período de graça em dias
- `maxdenybanners`: Máximo de banners de negação

#### 1.4. Sistema de Logging (`logger.py` + `loggers/`)

- `stderr`: Log para stderr
- `system`: Log para syslog

#### 1.5. Sistema de Relatórios (`reporter.py` + `reporters/`)

- `text`: Relatórios em texto
- `html`: Relatórios HTML

---

## Métodos de Contagem de Páginas

### 1. Software Accounting

**Como Funciona:**
1. Recebe o arquivo de impressão
2. Usa pkpgcounter para analisar o PDL
3. Retorna número de páginas

**Vantagens:**
- Funciona com qualquer impressora
- Não requer acesso à impressora
- Preciso para maioria dos formatos

**Desvantagens:**
- Pode falhar com formatos não suportados
- Requer processamento de CPU

**Configuração:**
```ini
[printer_name]
accounter = software
# ou
accounter = software(/usr/local/bin/pkpgcounter)
```

### 2. Hardware Accounting

**Como Funciona:**
1. Antes do job: lê contador interno da impressora
2. Envia job para impressora
3. Depois do job: lê contador novamente
4. Diferença = páginas impressas

**Métodos de Consulta:**

- **SNMP**: Para impressoras de rede
  ```ini
  accounter = hardware(snmp:community@host:oid)
  ```

- **PJL**: Para impressoras HP
  ```ini
  accounter = hardware(pjl)
  ```

- **Netatalk**: Para impressoras AppleTalk
  ```ini
  accounter = hardware(netatalk)
  ```

**Vantagens:**
- Muito preciso
- Não depende do formato do arquivo
- Conta páginas realmente impressas

**Desvantagens:**
- Requer acesso à impressora
- Pode falhar se impressora estiver offline
- Nem todas impressoras suportam

### 3. Ink Accounting

**Como Funciona:**
1. Analisa cada página do documento
2. Calcula porcentagem de cobertura por cor
3. Aplica coeficientes configurados
4. Calcula custo baseado em cobertura

**Espaços de Cor Suportados:**
- CMYK (Cyan, Magenta, Yellow, Black)
- CMY (Cyan, Magenta, Yellow)
- RGB (Red, Green, Blue)
- BW (Black, White)
- GC (Grayscale, Colored)

**Configuração:**
```ini
[printer_name]
accounter = ink(CMYK,150)
# Formato: ink(colorspace,resolution)

# Coeficientes por cor
coefficient_cyan = 1.5
coefficient_magenta = 1.5
coefficient_yellow = 1.0
coefficient_black = 1.0
```

**Exemplo de Cálculo:**
- Página com 50% cobertura de cyan
- Coeficiente cyan = 1.5
- Preço base por página = 0.10
- Custo = 0.10 * (1.5 * 0.50) = 0.075

---

## Sistema de Armazenamento

### Estrutura de Dados

#### Tabela: users
- `id`: ID único
- `username`: Nome do usuário
- `limitby`: Tipo de limite (quota, balance, noquota, noprint, nochange)
- `balance`: Saldo em créditos
- `lifetimepaid`: Total pago durante toda vida
- `email`: Email do usuário
- `overcharge`: Fator de sobrecobrança
- `description`: Descrição

#### Tabela: groups
- `id`: ID único
- `groupname`: Nome do grupo
- `limitby`: Tipo de limite
- `balance`: Saldo do grupo
- `lifetimepaid`: Total pago

#### Tabela: printers
- `id`: ID único
- `printername`: Nome da impressora
- `priceperpage`: Preço por página
- `priceperjob`: Preço por job
- `maxjobsize`: Tamanho máximo de job
- `passthrough`: Modo pass-through
- `description`: Descrição

#### Tabela: userpquota
- `id`: ID único
- `username`: Usuário
- `printername`: Impressora
- `pagecounter`: Páginas usadas (período atual)
- `lifepagecounter`: Páginas usadas (total)
- `softlimit`: Limite suave
- `hardlimit`: Limite rígido
- `datelimit`: Data limite (grace period)
- `warncount`: Contador de avisos
- `maxjobsize`: Tamanho máximo de job

#### Tabela: grouppquota
- Similar a userpquota, mas para grupos

#### Tabela: jobs
- `id`: ID único
- `username`: Usuário
- `printername`: Impressora
- `jobid`: ID do job CUPS
- `printerpagecounter`: Contador da impressora
- `jobsize`: Tamanho do job em páginas
- `jobprice`: Preço do job
- `jobdate`: Data/hora
- `jobfilename`: Nome do arquivo
- `jobtitle`: Título do job
- `jobcopies`: Número de cópias
- `joboptions`: Opções do job
- `jobhostname`: Host de origem
- `jobmd5sum`: MD5 do arquivo
- `jobpages`: Páginas do job
- `jobbillingcode`: Código de faturamento
- `precomputedjobsize`: Tamanho pré-computado
- `precomputedjobprice`: Preço pré-computado
- `action`: Ação (ALLOW, DENY, CANCEL, REFUND)

#### Tabela: lastjobs
- Último job por impressora (cache)

#### Tabela: payments
- Histórico de pagamentos/recargas

#### Tabela: billingcodes
- Códigos de faturamento

### Funcionalidades de Cache

O sistema implementa cache em memória para:
- Usuários
- Grupos
- Impressoras
- Cotas (userpquota, grouppquota)
- Últimos jobs
- Códigos de faturamento

Cache pode ser habilitado/desabilitado via configuração.

---

## Ferramentas de Linha de Comando

### 1. pkprinters - Gerenciamento de Impressoras

**Funcionalidades:**
- Adicionar/remover impressoras
- Configurar preços (por página, por job)
- Gerenciar grupos de impressoras
- Listar impressoras

**Exemplos:**
```bash
# Adicionar impressora
pkprinters --add --charge 0.05 hp2100

# Adicionar impressora com preço por job
pkprinters --add --charge 0.05 --jobprice 0.10 hp2100

# Listar impressoras
pkprinters --list

# Remover impressora
pkprinters --delete hp2100

# Adicionar a grupo
pkprinters --add --group colorprinters hp2100
```

### 2. pkusers - Gerenciamento de Usuários

**Funcionalidades:**
- Adicionar/remover usuários
- Configurar saldo
- Configurar tipo de limite
- Gerenciar grupos de usuários
- Listar usuários

**Exemplos:**
```bash
# Adicionar usuário com saldo
pkusers --add --limitby balance --balance 10.0 jerome

# Adicionar créditos
pkusers --balance +50.0 --comment "Recarga" jerome

# Configurar limite por quota
pkusers --limitby quota jerome

# Listar usuários
pkusers --list

# Remover usuário
pkusers --delete jerome
```

### 3. edpykota - Gerenciamento de Cotas

**Funcionalidades:**
- Criar cotas usuário-impressora
- Configurar limites (soft, hard)
- Resetar contadores
- Ajustar uso

**Exemplos:**
```bash
# Criar cota para usuário em impressora
edpykota --add --printer hp2100 jerome

# Configurar limites
edpykota --printer hp2100 --softlimit 100 --hardlimit 150 jerome

# Resetar contador
edpykota --printer hp2100 --reset jerome

# Ajustar uso manualmente
edpykota --printer hp2100 --used 50 jerome

# Listar cotas
edpykota --list --printer hp2100
```

### 4. repykota - Relatórios

**Funcionalidades:**
- Gerar relatórios de uso
- Filtrar por impressora, usuário, grupo
- Mostrar totais e estatísticas

**Exemplos:**
```bash
# Relatório geral
repykota

# Relatório por impressora
repykota --printer hp2100

# Relatório de grupos
repykota --groups

# Relatório de usuários específicos
repykota jerome paul george
```

### 5. dumpykota - Exportação de Dados

**Funcionalidades:**
- Exportar dados em múltiplos formatos
- Filtrar por critérios diversos
- Ordenar resultados

**Formatos Suportados:**
- CSV (Comma Separated Values)
- SSV (Semicolon Separated Values)
- TSV (Tabulation Separated Values)
- XML (eXtensible Markup Language)
- CUPS (formato page_log do CUPS)

**Tipos de Dados:**
- history: Histórico de jobs
- users: Usuários
- groups: Grupos
- printers: Impressoras
- upquotas: Cotas de usuários
- gpquotas: Cotas de grupos
- payments: Pagamentos
- billingcodes: Códigos de faturamento
- all: Todos os dados

**Exemplos:**
```bash
# Exportar histórico em CSV
dumpykota --data history --format csv > history.csv

# Exportar usuários em XML
dumpykota --data users --format xml > users.xml

# Filtrar por data
dumpykota --data history --filter start=20240101 --filter end=20241231

# Filtrar por impressora
dumpykota --data history --filter printername=hp2100
```

### 6. pkrefund - Reembolso de Jobs

**Funcionalidades:**
- Reembolsar jobs impressos
- Restaurar saldo/cota do usuário
- Registrar motivo do reembolso

**Exemplos:**
```bash
# Reembolsar job específico
pkrefund --jobid 123 --reason "Erro de impressão"

# Reembolsar múltiplos jobs
pkrefund --jobid 123,124,125 --reason "Problema técnico"
```

### 7. pkbcodes - Códigos de Faturamento

**Funcionalidades:**
- Criar/gerenciar códigos de faturamento
- Associar jobs a códigos
- Relatórios por código

**Exemplos:**
```bash
# Criar código
pkbcodes --add PROJETO_A

# Listar códigos
pkbcodes --list

# Ver uso de código
pkbcodes --list PROJETO_A
```

### 8. pkinvoice - Geração de Faturas

**Funcionalidades:**
- Gerar faturas em PDF
- Filtrar por período, usuário, impressora
- Usa ReportLab para geração

**Exemplos:**
```bash
# Fatura para usuário
pkinvoice --user jerome --start 20240101 --end 20241231

# Fatura para impressora
pkinvoice --printer hp2100 --start 20240101
```

### 9. pkbanner - Banners de Impressão

**Funcionalidades:**
- Gerar banners de início/fim de job
- Personalizáveis via templates
- Suporta imagens (PIL)

**Tipos de Banner:**
- Starting banner: No início do job
- Ending banner: No fim do job
- Deny banner: Quando job é negado

**Configuração:**
```ini
[printer_name]
startingbanner = /path/to/template.ps
endingbanner = /path/to/template.ps
accountbanner = BOTH  # NONE, BOTH, STARTING, ENDING
```

### 10. pknotify - Notificações

**Funcionalidades:**
- Enviar notificações para clientes
- Confirmar impressões antes de executar
- Integração com pykoticon (cliente Windows)

**Uso:**
```bash
# Notificar usuário sobre job
pknotify --destination hostname:7654 --timeout 7 --confirm "Mensagem"
```

**Configuração:**
```ini
[printer_name]
askconfirmation = /usr/local/bin/pknotify --destination $PYKOTAJOBORIGINATINGHOSTNAME:7654 --timeout 7 --confirm "Hello $PYKOTAUSERNAME.\nThe job $PYKOTAJOBID will cost $PYKOTAPRECOMPUTEDJOBSIZE page(s)"
```

### 11. pkmail - Envio de Emails

**Funcionalidades:**
- Enviar emails para usuários/admins
- Templates personalizáveis
- Suporte a múltiplos destinatários

### 12. pykosd - On-Screen Display

**Funcionalidades:**
- Mostrar saldo/cota restante na tela
- Requer X Window System
- Usa pyosd para exibição

### 13. pykotme - Cotações Pré-Impressão

**Funcionalidades:**
- Calcular custo antes de imprimir
- Permite usuário escolher impressora mais barata
- Analisa arquivo e calcula páginas/custo

**Exemplos:**
```bash
# Cotações para arquivo
pykotme --printer hp2100 document.pdf

# Cotações para múltiplas impressoras
pykotme --printer "*" document.pdf
```

### 14. warnpykota - Avisos de Cota

**Funcionalidades:**
- Verificar cotas e enviar avisos
- Pode ser executado via cron
- Envia emails quando cota está baixa

### 15. autopykota - Criação Automática de Contas

**Funcionalidades:**
- Criar contas automaticamente no primeiro print
- Usado via política EXTERNAL
- Configurável

**Configuração:**
```ini
[printer_name]
policy = EXTERNAL(/usr/local/bin/autopykota)
```

### 16. pkturnkey - Configuração Automática

**Funcionalidades:**
- Ajuda na configuração inicial
- Detecta melhor método de contagem
- Gera configurações sugeridas

**Exemplos:**
```bash
# Obter sugestões de configuração
pkturnkey --doconf TheNameOfThePrintQueue
```

### 17. pksetup - Instalação Interativa

**Funcionalidades:**
- Instalação guiada (Debian/Ubuntu)
- Configura banco de dados
- Cria usuários e estrutura

---

## Backend CUPS

### cupspykota - Backend Principal

O `cupspykota` é um backend CUPS que intercepta todos os jobs de impressão.

**Funcionalidades Principais:**

1. **Interceptação de Jobs**
   - CUPS chama `cupspykota://...` em vez do backend real
   - Backend extrai URI real e processa job

2. **Ciclo de Vida do Job**
   ```
   Início → Pré-contagem → Verificação de Cota → Impressão → Pós-contagem → Atualização BD
   ```

3. **Processamento de Dados**
   - Salva arquivo temporário
   - Calcula MD5 para detecção de duplicatas
   - Chama accounter para contagem

4. **Gerenciamento de Erros**
   - Retry em caso de falha
   - Fallback para métodos alternativos
   - Logging detalhado

5. **Lock Files**
   - Previne processamento simultâneo
   - Suporta NFS
   - Baseado em fcntl

6. **Integração com IPP**
   - Usa pkipplib para comunicação IPP
   - Obtém atributos de job
   - Monitora status da impressora

**Variáveis de Ambiente (CUPS → PyKota):**

- `PYKOTAUSERNAME`: Nome do usuário
- `PYKOTAPRINTERNAME`: Nome da impressora
- `PYKOTAJOBID`: ID do job
- `PYKOTAJOBORIGINATINGHOSTNAME`: Host de origem
- `PYKOTABALANCE`: Saldo atual
- `PYKOTAPRECOMPUTEDJOBSIZE`: Tamanho pré-computado
- `PYKOTAPRECOMPUTEDJOBPRICE`: Preço pré-computado

**Ações Possíveis:**

- `ALLOW`: Job permitido, prossegue
- `DENY`: Job negado, cancela
- `WARN`: Job permitido, mas envia aviso
- `POLICY_ALLOW`: Permitido por política padrão
- `POLICY_DENY`: Negado por política padrão
- `CANCEL`: Job cancelado
- `REFUND`: Job reembolsado

---

## Sistema de Configuração

### Arquivo: pykota.conf

**Estrutura:**
```ini
[global]
# Configurações globais
storagebackend = postgresql
storageserver = localhost
storagename = pykota
storageuser = pykota
storageuserpw = password

logger = system
debug = no
privacy = no
storagecaching = yes

[printer_name]
# Configurações específicas da impressora
accounter = software
preaccounter = software
policy = DENY
enforcement = LAXIST
mailto = BOTH
gracedelay = 7
maxdenybanners = 3
```

### Principais Diretivas

#### Diretivas Globais

- `storagebackend`: Backend (postgresql, mysql, sqlite, ldap)
- `storageserver`: Servidor de banco
- `storagename`: Nome do banco
- `storageuser`: Usuário do banco
- `storageuserpw`: Senha do banco
- `logger`: Backend de log (stderr, system)
- `debug`: Modo debug (yes, no)
- `privacy`: Ocultar títulos/arquivos (yes, no)
- `storagecaching`: Cache de banco (yes, no)
- `disablehistory`: Desabilitar histórico (yes, no)
- `smtpserver`: Servidor SMTP
- `maildomain`: Domínio de email
- `poorman`: Limite de "pobre" (saldo baixo)
- `balancezero`: Valor considerado zero
- `poorwarn`: Mensagem de aviso de saldo baixo

#### Diretivas por Impressora

- `accounter`: Método de contagem (software, hardware, ink)
- `preaccounter`: Pré-contagem (opcional)
- `policy`: Política padrão (ALLOW, DENY, EXTERNAL)
- `enforcement`: Aplicação (STRICT, LAXIST)
- `mailto`: Destinatários (USER, ADMIN, BOTH, EXTERNAL, NOBODY)
- `adminmail`: Email do administrador
- `admin`: Nome do administrador
- `gracedelay`: Período de graça (dias)
- `maxdenybanners`: Máximo de banners de negação
- `printcancelledbanners`: Imprimir banner quando cancelado
- `hardwarn`: Mensagem de limite rígido
- `softwarn`: Mensagem de limite suave
- `onbackenderror`: Ação em erro de backend (CHARGE, NOCHARGE, RETRY)
- `onaccountererror`: Ação em erro de accounter (CONTINUE, STOP)
- `keepfiles`: Manter arquivos temporários
- `directory`: Diretório de trabalho
- `denyduplicates`: Negar jobs duplicados
- `duplicatesdelay`: Delay para considerar duplicado
- `startingbanner`: Template de banner inicial
- `endingbanner`: Template de banner final
- `accountbanner`: Contabilizar banners (NONE, BOTH, STARTING, ENDING)
- `avoidduplicatebanners`: Evitar banners duplicados
- `trustjobsize`: Confiar no tamanho do job
- `coefficient_*`: Coeficientes para ink accounting

### Arquivo: pykotadmin.conf

Contém credenciais administrativas:
- `storageadmin`: Usuário admin do banco
- `storageadminpw`: Senha admin

---

## Sistema de Relatórios

### Tipos de Relatório

1. **Relatórios de Texto** (`reporters/text.py`)
   - Formato tabular
   - Saída para stdout
   - Fácil de processar

2. **Relatórios HTML** (`reporters/html.py`)
   - Formatação rica
   - Cores para violações
   - Links e navegação

### Informações Incluídas

- Nome do usuário/grupo
- Fator de sobrecobrança
- Páginas usadas
- Limites (soft, hard)
- Saldo atual
- Período de graça
- Total de páginas (vida)
- Total pago
- Contador de avisos

### CGI Scripts

- `printquota.cgi`: Interface web para relatórios
- `dumpykota.cgi`: Interface web para exportação
- `pykotme.cgi`: Interface web para cotações

---

## Funcionalidades Avançadas

### 1. Hierarquia de Impressoras

Impressoras podem pertencer a grupos, e grupos podem ter grupos pais.

**Exemplo:**
```
colorprinters (grupo)
  ├── hp2100 (impressora)
  └── canon (impressora)
```

Quando usuário imprime em `hp2100`, cotas são verificadas em:
1. `hp2100` (impressora específica)
2. `colorprinters` (grupo pai)

### 2. Grupos de Usuários

Usuários podem pertencer a grupos, e grupos têm cotas próprias.

**Verificação de Cota:**
1. Verifica cotas de grupos do usuário
2. Verifica cota individual do usuário
3. Aplica política mais restritiva

### 3. Políticas de Impressão

**ALLOW**: Permite impressão mesmo sem cota configurada
**DENY**: Nega impressão se não houver cota
**EXTERNAL**: Delega decisão para comando externo

**Exemplo EXTERNAL:**
```ini
[printer_name]
policy = EXTERNAL(/usr/local/bin/autopykota)
```

### 4. Modos de Aplicação

**STRICT**: Verifica cota considerando o job atual
- Se job atual exceder limite, nega

**LAXIST**: Verifica cota sem considerar job atual
- Permite job mesmo se exceder limite
- Útil para jobs já iniciados

### 5. Período de Graça (Grace Period)

Quando usuário atinge soft limit:
- Recebe aviso (WARN)
- Define data limite (gracedelay dias)
- Pode imprimir até data limite
- Após data limite, nega (DENY)

### 6. Detecção de Duplicatas

Pode detectar e negar jobs duplicados baseado em:
- MD5 do arquivo
- Nome do arquivo
- Tamanho
- Delay configurável

### 7. Códigos de Faturamento

Jobs podem ser associados a códigos de faturamento:
- Projetos
- Departamentos
- Clientes
- Etc.

Permite relatórios por código.

### 8. Sobre-cobrança (Overcharge)

Usuários podem ter fator de sobre-cobrança:
- `1.0`: Cobrança normal
- `1.5`: 50% a mais
- `0.0`: Grátis

### 9. Limites por Data

Cotas podem ter data limite:
- Útil para cotas mensais/anuais
- Reset automático após data

### 10. Banners Personalizados

Banners podem ser gerados dinamicamente com:
- Informações do job
- Informações do usuário
- Saldo/cota atual
- Templates PostScript

### 11. Hooks (Pre/Post)

Comandos podem ser executados antes/depois do job:

```ini
[printer_name]
prehook = /path/to/script.sh
posthook = /path/to/script.sh
```

### 12. Confirmação de Impressão

Usuário pode ser solicitado a confirmar antes de imprimir:
- Via pknotify
- Timeout configurável
- Mostra custo estimado

### 13. Privacidade

Modo privacidade oculta:
- Nome do arquivo
- Título do job
- Opções do job

Útil para ambientes sensíveis.

### 14. Histórico Detalhado

Cada job armazena:
- Data/hora
- Usuário
- Impressora
- Tamanho (páginas)
- Preço
- Nome do arquivo
- Título
- Cópias
- Opções
- Host de origem
- MD5
- Código de faturamento
- Ação (ALLOW, DENY, etc.)

### 15. Suporte a Múltiplos Idiomas

Sistema suporta internacionalização:
- Mensagens traduzidas
- Manuais em múltiplos idiomas
- Locale-aware

---

## Integração com pkpgcounter

pkpgcounter é um parser genérico de PDL que suporta:

**Formatos Suportados:**
- PostScript (DSC e binário)
- PDF
- PCL3/4/5
- PCLXL (PCL6)
- DVI
- OpenDocument
- Microsoft Word
- Plain text
- TIFF
- ESC/P2
- ZjStream
- Samsung QPDL/SPL1
- ESC/PageS03
- Brother HBP/XL2HB
- HP LIDIL
- Structured Fax
- Canon BJ/BJC
- ASCII PNM

**Funcionalidades:**
- Contagem de páginas
- Cálculo de cobertura de tinta
- Múltiplos espaços de cor
- Resolução configurável

---

## Integração com pkipplib

pkipplib fornece:

**Funcionalidades:**
- Construção de requisições IPP
- Parsing de respostas IPP
- API de alto nível para CUPS
- Suporte a operações IPP completas

**Uso no PyKota:**
- Obter atributos de job
- Monitorar status de impressora
- Comunicar com CUPS server

---

## Considerações para Migração para Go

### Funcionalidades Críticas a Implementar

1. **Backend CUPS**
   - Interceptar jobs CUPS
   - Gerenciar ciclo de vida
   - Integração com backends reais

2. **Sistema de Contagem**
   - Software: Integrar com parser PDL (ou criar)
   - Hardware: SNMP, PJL, etc.
   - Ink: Cálculo de cobertura

3. **Sistema de Armazenamento**
   - Abstração de banco
   - Suporte a PostgreSQL (prioritário)
   - Cache em memória
   - Transações

4. **Sistema de Configuração**
   - Parser de arquivos de configuração
   - Validação
   - Hierarquia (global + por impressora)

5. **Ferramentas CLI**
   - Gerenciamento de usuários
   - Gerenciamento de impressoras
   - Gerenciamento de cotas
   - Relatórios
   - Exportação

6. **Sistema de Logging**
   - Integração com sistema de log
   - Níveis de log
   - Rotação

7. **Sistema de Notificações**
   - Email
   - Notificações em tempo real
   - Banners

8. **API REST** (novo)
   - Endpoints para operações
   - Autenticação
   - Documentação OpenAPI

### Desafios Técnicos

1. **Parser PDL**: pkpgcounter é extenso, pode precisar de biblioteca Go ou binding
2. **Integração CUPS**: Pode precisar de biblioteca Go para CUPS ou usar CGO
3. **Performance**: Go deve ser mais rápido que Python
4. **Concorrência**: Go facilita processamento paralelo
5. **Deploy**: Binário único vs múltiplos scripts Python

---

## Conclusão

PyKota é um sistema complexo e completo de gerenciamento de cotas de impressão. A migração para Go deve manter todas as funcionalidades principais enquanto aproveita as vantagens de performance e deploy do Go.

**Prioridades para GOecoprint:**
1. Backend CUPS básico
2. Sistema de armazenamento (PostgreSQL)
3. Contagem software (básica)
4. Gerenciamento de usuários/impressoras/cotas
5. Verificação de cotas
6. Relatórios básicos
7. Funcionalidades avançadas progressivamente

