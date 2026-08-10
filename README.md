# Sistema OCR Multi-Provider + IA + RPA + Excel

Sistema completo para automatizar o processamento de comprovantes financeiros e preencher uma planilha Excel mestre, utilizando **múltiplos mecanismos de OCR/IA** com consenso e detecção de divergências.

## Arquitetura

```
Documento (JPG/PNG/PDF/...)
    ↓
Detectar formato
    ↓
┌───────────┬──────────────┐
↓           ↓              ↓
PDF         PDF Escaneado  Imagem
Digital     ↓              ↓
↓           Multi-Provider  Multi-Provider
pdfplumber  OCR (paralelo)  OCR (paralelo)
PyMuPDF     ↓              ↓
↓           ┌──────────────┐
↓           ├ PaddleOCR    │ (local)
↓           ├ Gemini       │ (multimodal)
↓           ├ Qwen-VL      │ (Ollama/HF)
↓           └ OpenAI Vision│ (opcional)
↓           ↓
↓           Comparador de resultados
↓           ↓
↓        CONSENSO / DIVERGÊNCIA
↓           ↓
└──────────>↓
            Validação Python
            ↓
            Regras de negócio
            ↓
            Excel (openpyxl)
```

## Providers de OCR

| Provider | Tipo | Dependência | Obrigatório |
|----------|------|-------------|-------------|
| **PaddleOCR** | Local | `paddlepaddle`, `paddleocr` | ✅ Sim (principal fallback) |
| **Gemini** | API (Google) | `google-genai` | ❌ Opcional (conferência) |
| **Qwen-VL** | Local (Ollama) | Ollama + `qwen2.5vl:3b` | ❌ Opcional (conferência) |
| **OpenAI Vision** | API (OpenAI) | `openai` | ❌ Opcional |

### Fluxo de Consenso

```
Imagem
 ↓
Pré-processamento existente
 ↓
 ├── PaddleOCR ─────┐
 ├── Gemini ────────┤ (executados em paralelo)
 └── Qwen-VL ───────┘
 ↓
Comparador (OCRResultComparator)
 ↓
├── 3/3 concordam     → CONFIRMED / HIGH
├── 2/3 concordam     → CONSENSUS / MEDIUM-HIGH + aviso
├── 1/3 concorda      → DIVERGENT / LOW + aviso
└── Nenhum funciona   → OCR_FAILED (sem crash)
```

### OpenAI Sem Créditos (429 / insufficient_quota / credit_balance_exhausted)

```
OpenAI
   ↓
429 / insufficient_quota / credit_balance_exhausted
   ↓
Registrar WARNING
   ↓
Desabilitar OpenAI durante esta execução
   ↓
PaddleOCR + Gemini + Qwen-VL continuam normalmente
   ↓
Comparação e consenso
```

O sistema **não** fica tentando a OpenAI repetidamente após detectar falta de créditos.

## Requisitos

- **Python 3.10+**
- **Windows 10/11**
- **16GB RAM** (para rodar Qwen2.5-VL-3B localmente via Ollama)
- Chave de API do Google Gemini (opcional, para conferência)
- Chave de API da OpenAI (opcional)

## Instalação

### 1. Clonar/copiar o projeto

```bash
cd C:\Users\SeuUsuario\Desktop
# Copiar pasta projeto_ocr_rpa para o Desktop
```

### 2. Criar ambiente virtual

```bash
cd projeto_ocr_rpa
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Instalar Ollama (para Qwen-VL)

1. Baixe e instale o Ollama: https://ollama.com/download
2. Após instalar, execute no terminal:
```bash
ollama pull qwen2.5vl:3b
```
3. O modelo `qwen2.5vl:3b` (~2GB quantizado) é leve o suficiente para **16GB RAM sem GPU dedicada**.
4. Verifique se o Ollama está rodando: http://localhost:11434

### 5. Configurar API Keys

```bash
copy .env.example .env
```

Edite o arquivo `.env` e preencha:
```
# Google Gemini (obtenha em: https://aistudio.google.com/apikey)
GEMINI_API_KEY=sua-chave-aqui

# OpenAI (opcional - o sistema funciona sem ela)
OPENAI_API_KEY=sk-sua-chave-aqui
```

### 6. Verificar PaddleOCR

```bash
python -c "from paddleocr import PaddleOCR; print('PaddleOCR OK')"
```

Se falhar, reinstale:
```bash
pip install paddlepaddle paddleocr
```

### 7. Configurar planilha Excel

O arquivo `Controle Financeiro Geral.xlsx` já vem com cabeçalhos padrão.
Se você já tem uma planilha, coloque-a na raiz do projeto com o mesmo nome (ou configure o caminho no `.env`).

### 8. Configurar WhatsApp (opcional)

No `.env`, configure o caminho das imagens do WhatsApp:
```
WHATSAPP_PATH=%USERPROFILE%\Downloads\WhatsApp Images
```

## Configuração (.env)

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `OPENAI_ENABLED` | Habilitar OpenAI Vision | `true` |
| `OPENAI_API_KEY` | Chave da API OpenAI | (vazio) |
| `OPENAI_MODEL` | Modelo OpenAI | `gpt-4o` |
| `PADDLEOCR_ENABLED` | Habilitar PaddleOCR local | `true` |
| `GEMINI_ENABLED` | Habilitar Google Gemini | `true` |
| `GEMINI_API_KEY` | Chave da API Gemini | (vazio) |
| `GEMINI_MODEL` | Modelo Gemini | `gemini-2.0-flash` |
| `QWEN_ENABLED` | Habilitar Qwen-VL | `true` |
| `QWEN_MODEL` | Modelo Qwen (Ollama) | `qwen2.5vl:3b` |
| `QWEN_BASE_URL` | URL base Ollama | `http://localhost:11434` |
| `OCR_REQUIRE_CONSENSUS` | Exigir consenso | `true` |
| `OCR_MIN_CONFIDENCE` | Confiança mínima | `0.80` |
| `EXCEL_PATH` | Caminho da planilha | `Controle Financeiro Geral.xlsx` |
| `ENTRADA_PATH` | Pasta de entrada | `arquivos/entrada` |
| `PROCESSADOS_PATH` | Pasta de processados | `arquivos/processados` |
| `FALHAS_PATH` | Pasta de falhas | `arquivos/falhas` |
| `WHATSAPP_PATH` | Pasta WhatsApp Images | (vazio) |
| `DATABASE_PATH` | Banco SQLite | `banco/processamento.db` |
| `LOG_PATH` | Arquivo de log | `logs/processamento.log` |
| `MAX_WORKERS` | Workers paralelos | `4` |
| `LOCAL_OCR_FALLBACK` | Habilitar fallback OCR | `true` |
| `DELETE_PROCESSED_FILES` | Excluir após processar | `false` |

## Uso

### Modo Monitoramento (principal)

```bash
python main.py
```

O sistema:
1. Processa arquivos existentes em `arquivos/entrada/`
2. Monitora a pasta por novos arquivos
3. Monitora a pasta do WhatsApp (se configurada)
4. Processa automaticamente cada novo arquivo detectado
5. Pressione Ctrl+C para parar

### Modo Lote (processar uma vez)

```bash
python processar_uma_vez.py
```

### Executar testes

```bash
pytest testes/ -v
```

Para rodar apenas os testes do novo sistema multi-provider:

```bash
pytest testes/test_ocr_multi_provider.py -v
```

### Testes incluídos

| Teste | Cenário | Esperado |
|-------|---------|----------|
| 1 | OpenAI funcionando | Extração com sucesso |
| 2 | OpenAI 429 credit_balance_exhausted | Programa continua sem crash |
| 3 | PaddleOCR funcionando | Texto + confiança |
| 4 | PaddleOCR indisponível | Erro controlado, sem crash |
| 5 | Gemini funcionando | Extração com sucesso |
| 6 | Gemini indisponível | Erro controlado, sem crash |
| 7 | Qwen-VL funcionando | Extração com sucesso |
| 8 | Qwen-VL indisponível | Erro controlado, sem crash |
| 9 | Todos retornam mesmo texto | `CONFIRMED` / `HIGH` |
| 10 | Dois iguais, um diferente | `CONSENSUS` + divergência |
| 11 | Todos diferentes | `DIVERGENT` / `LOW` |
| 12 | Nenhum provider funciona | `OCR_FAILED` sem crash |

## Estrutura do Projeto

```
projeto_ocr_rpa/
│
├── main.py                    # Monitoramento com watchdog
├── processar_uma_vez.py       # Processamento em lote
├── config.py                  # Configuração centralizada
├── logger.py                  # Logging com rotação
├── utils.py                   # Funções utilitárias
├── database.py                # Banco SQLite
├── requirements.txt           # Dependências
├── README.md                  # Este arquivo
├── .env.example               # Exemplo de configuração
├── .gitignore
│
├── Controle Financeiro Geral.xlsx  # Planilha mestre
│
├── ocr/                       # ⭐ Sistema multi-provider OCR
│   ├── __init__.py
│   ├── providers.py           # OpenAI, PaddleOCR, Gemini, Qwen-VL
│   ├── comparator.py          # Normalização, consenso, divergência
│   └── manager.py             # Orquestrador (singleton, paralelo)
│
├── openai_reader/             # Integração com OpenAI
│   ├── __init__.py
│   ├── client.py              # Cliente com retry (429 sem retry)
│   ├── prompts.py             # Prompts para a IA
│   ├── extractor.py           # Extração de dados
│   └── schemas.py             # Schema Pydantic
│
├── leitor/                    # Leitura de documentos
│   ├── __init__.py
│   ├── imagem.py              # Carregamento de imagens
│   ├── pdf.py                 # Extração de texto de PDFs
│   └── ocr.py                 # OCR local (fallback)
│
├── processamento/             # Pipeline de processamento
│   ├── __init__.py
│   ├── preprocessamento.py    # Pré-processamento OpenCV
│   ├── classificacao.py       # Classificação de documentos
│   ├── extracao.py            # Orquestração da extração
│   ├── validacao.py           # Validação de dados
│   ├── regras.py              # Regras de negócio
│   └── normalizacao.py        # Normalização de dados
│
├── excel/                     # Excel
│   ├── __init__.py
│   ├── excel.py               # Escrita thread-safe
│   ├── mapping.py             # Mapeamento de colunas
│   └── automacao.py           # Automação auxiliar
│
├── arquivos/                  # Arquivos de trabalho
│   ├── entrada/               # Documentos a processar
│   ├── processados/           # Documentos processados
│   └── falhas/                # Documentos com falha
│
├── logs/                      # Logs com rotação
│   └── processamento.log
│
├── banco/                     # Banco SQLite
│   └── processamento.db
│
└── testes/                    # Testes unitários
    ├── test_ocr_multi_provider.py  # ⭐ Testes do multi-provider
    ├── test_utils.py
    ├── test_validacao.py
    ├── test_regras.py
    ├── test_extracao.py
    ├── test_openai.py
    ├── test_excel.py
    ├── test_normalizacao.py
```

## Como o novo fluxo funciona

### 1. Imagem chega ao sistema

O `processamento/extracao.py` detecta que é uma imagem e chama o `OCRManager`.

### 2. Providers executam em paralelo

O `ocr/manager.py` (singleton — modelos carregados apenas **uma vez**) executa todos os providers habilitados em paralelo via `ThreadPoolExecutor`:

```python
manager = OCRManager()
resultado = manager.analisar_imagem(filepath)
```

### 3. Cada provider retorna estrutura padronizada

```python
{
    "provider": "paddleocr",
    "success": True,
    "text": "Pedido 12345\nValor R$ 150,00",
    "confidence": 0.94,
    "error": None
}
```

### 4. Normalização antes da comparação

O `ocr/comparator.py` normaliza os textos (espaços, quebras de linha, maiúsculas) **preservando dados críticos**:

- Números
- Valores monetários (`R$ 150,00` vs `R$ 180,00` → diferentes)
- Datas
- CPF/CNPJ
- Códigos/números de pedido

### 5. Consenso e divergência

O `OCRResultComparator` agrupa os resultados por texto normalizado:

- **3/3 concordam** → `CONFIRMED` / `HIGH`
- **2/3 concordam** → `CONSENSUS` + aviso do provider discordante
- **Todos diferentes** → `DIVERGENT` / `LOW` + notificação

### 6. Confiança

```
3/3 concordam            → HIGH
2/3 concordam (3 total)  → MEDIUM/HIGH
PaddleOCR conf < 0.80    → rebaixa um nível
1/3 concorda             → LOW
Nenhum resultado         → VERY_LOW
```

### 7. Divergência detectada

```python
WARNING | OCR | DIVERGÊNCIA DETECTADA
WARNING | OCR | Status: DIVERGENT
WARNING | OCR | Confiança: LOW
```

Usa `notify_ocr_divergence(...)` — ponto de extensão para Discord, Telegram, e-mail ou webhook.

### 8. OpenAI sem créditos

```python
WARNING | OCR | OpenAI Vision indisponível por falta de créditos
INFO | OCR | Continuando com PaddleOCR, Gemini e Qwen-VL
```

O flag `_OPENAI_SEM_CREDITOS` desabilita novas chamadas à OpenAI durante toda a execução atual.

## Troubleshooting

### "OPENAI_API_KEY não configurada"
O sistema funciona sem OpenAI. Verifique se `OPENAI_ENABLED=true` no `.env` e se outras chaves estão configuradas.

### "GEMINI_API_KEY não configurada"
Obtenha uma chave gratuita em: https://aistudio.google.com/apikey

### "Qwen-VL não disponível"
1. Instale o Ollama: https://ollama.com/download
2. Execute: `ollama pull qwen2.5vl:3b`
3. Verifique: http://localhost:11434

### "PaddleOCR não instalado"
Instale com: `pip install paddlepaddle paddleocr`

### "Excel está aberto ou sem permissão"
Feche o arquivo Excel antes de processar documentos.

### Logs
Verifique `logs/processamento.log` para detalhes de erros.

### Arquivos na pasta de falhas
Cada arquivo em `arquivos/falhas/` tem um `.json` associado com diagnóstico do erro.

## Regras de Negócio

### Entrada
Pagadores conhecidos (Joyce, Diego, Ricardo, etc.) são classificados como **Entrada**.

### Saída
- Pagador = PORTES ENGENHARIA → **Saída**
- Tipo = Getnet, Sicoob, Nota Jandibloc → **Saída**

### Nome do Arquivo (Prioridade Máxima)
O nome do arquivo sobrescreve dados da IA:
- `Cliente - Local - Servico.jpg` → nome, cidade, descrição
- `Cliente - Servico.jpg` → nome, descrição