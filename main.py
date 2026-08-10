"""
Sistema principal com monitoramento via watchdog.

Monitora a pasta de entrada e a pasta do WhatsApp por novos arquivos.
Ao detectar um novo arquivo suportado, executa o pipeline completo:
  Deteccao -> Estabilidade -> MD5 -> Extracao -> Validacao -> Regras -> Excel -> Banco

Uso:
  python main.py
"""

from __future__ import annotations

import json
import shutil
import signal
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, Future
from pathlib import Path
from threading import Event

from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent
from watchdog.observers import Observer

from config import (
    DELETE_PROCESSED_FILES,
    ENTRADA_PATH,
    FALHAS_PATH,
    MAX_WORKERS,
    PROCESSADOS_PATH,
    WHATSAPP_PATH,
)
from database import (
    hash_ja_processado,
    inicializar_banco,
    registrar_falha,
    registrar_inicio,
    registrar_sucesso,
)
from logger import log
from utils import arquivo_estavel, calcular_md5, extensao_suportada, parsear_nome_arquivo, mover_arquivo
from processamento.extracao import extrair_dados_documento
from processamento.normalizacao import normalizar_documento_extraido
from processamento.classificacao import classificar_documento
from processamento.validacao import validar_dados_extraidos
from processamento.regras import determinar_direcao, aplicar_dados_nome_arquivo, verificar_confianca_minima
from excel.excel import escrever_no_excel

# Evento para shutdown gracioso
_shutdown = Event()


# ============================================================
# PIPELINE DE PROCESSAMENTO (executa em worker)
# ============================================================

def processar_arquivo(caminho_str: str) -> dict:
    """
    Pipeline completo de processamento de um documento.

    Executado em processo separado (ProcessPoolExecutor).
    Recebe caminho como string (serializavel entre processos).
    Retorna dict com resultado do processamento.
    """
    caminho = Path(caminho_str)
    inicio = time.time()
    resultado: dict = {
        "arquivo": caminho.name,
        "status": "falha",
        "erro": None,
        "dados": None,
        "tempo": 0.0,
    }

    try:
        # 1. Verificar se arquivo ainda existe
        if not caminho.exists():
            resultado["erro"] = "Arquivo nao encontrado."
            return resultado

        # 2. Aguardar estabilidade (arquivo pode estar sendo copiado)
        if not arquivo_estavel(caminho):
            resultado["erro"] = "Arquivo instavel (pode estar sendo copiado)."
            return resultado

        # 3. Calcular MD5
        hash_md5 = calcular_md5(caminho)

        # 4. Verificar duplicata
        if hash_ja_processado(hash_md5):
            resultado["status"] = "duplicado"
            resultado["erro"] = f"Arquivo ja processado (MD5: {hash_md5})."
            return resultado

        # 5. Registrar inicio no banco
        registro_id = registrar_inicio(hash_md5, caminho.name, str(caminho))

        # 6. Extrair dados (OpenAI + fallback local)
        extracao = extrair_dados_documento(caminho)
        dados = extracao.get("dados") or {}
        texto_bruto = extracao.get("texto_bruto", "")
        erro_extracao = extracao.get("erro")

        if not dados and erro_extracao:
            resultado["erro"] = erro_extracao
            tempo = time.time() - inicio
            resultado["tempo"] = tempo
            registrar_falha(
                registro_id, erro_extracao,
                tempo_processamento=tempo,
                modelo_openai=extracao.get("modelo"),
                tokens_entrada=extracao.get("tokens_entrada"),
                tokens_saida=extracao.get("tokens_saida"),
                custo_estimado=extracao.get("custo_estimado"),
            )
            _mover_para_falhas(caminho, erro_extracao, dados, hash_md5)
            return resultado

        # 7. Normalizar (ja feito dentro de extrair_dados_documento, mas garantir)
        if dados:
            dados = normalizar_documento_extraido(dados)

        # 8. Classificar
        classif = classificar_documento(
            tipo_ia=dados.get("tipo_documento"),
            texto_documento=texto_bruto,
            dados_ia=dados,
        )
        dados["tipo_documento"] = classif["tipo_final"]
        if classif["divergencia"]:
            obs = dados.get("observacoes") or ""
            dados["observacoes"] = (obs + " [DIVERGENCIA NA CLASSIFICACAO]").strip()

        # 9. Validar
        validacao = validar_dados_extraidos(dados)

        # 10. Aplicar regras de negocio
        direcao = determinar_direcao(
            pagador=dados.get("pagador"),
            recebedor=dados.get("recebedor"),
            tipo_documento=dados.get("tipo_documento"),
            dados=dados,
        )
        dados["direcao"] = direcao

        # 11. Parsing do nome do arquivo (prioridade maxima)
        info_nome = parsear_nome_arquivo(caminho)
        dados = aplicar_dados_nome_arquivo(dados, info_nome)

        # 12. Verificar confianca
        if not verificar_confianca_minima(dados, limiar=0.3):
            resultado["erro"] = f"Confianca muito baixa: {dados.get('confianca')}"
            resultado["dados"] = dados
            tempo = time.time() - inicio
            resultado["tempo"] = tempo
            registrar_falha(
                registro_id, resultado["erro"], dados_parciais=dados,
                tempo_processamento=tempo,
                modelo_openai=extracao.get("modelo"),
                tokens_entrada=extracao.get("tokens_entrada"),
                tokens_saida=extracao.get("tokens_saida"),
                custo_estimado=extracao.get("custo_estimado"),
            )
            _mover_para_falhas(caminho, resultado["erro"], dados, hash_md5)
            return resultado

        # 13. Verificar validacao
        if not validacao["valido"]:
            log.warning(f"Validacao com erros para {caminho.name}: {validacao['erros']}")
            # Nao aborta, apenas registra os avisos

        # 14. Escrever no Excel
        excel_ok = escrever_no_excel(dados)
        if not excel_ok:
            resultado["erro"] = "Falha ao escrever no Excel."
            resultado["dados"] = dados
            tempo = time.time() - inicio
            resultado["tempo"] = tempo
            registrar_falha(
                registro_id, resultado["erro"], dados_parciais=dados,
                tempo_processamento=tempo,
                modelo_openai=extracao.get("modelo"),
                tokens_entrada=extracao.get("tokens_entrada"),
                tokens_saida=extracao.get("tokens_saida"),
                custo_estimado=extracao.get("custo_estimado"),
            )
            _mover_para_falhas(caminho, resultado["erro"], dados, hash_md5)
            return resultado

        # 15. Registrar sucesso no banco
        tempo = time.time() - inicio
        registrar_sucesso(
            registro_id=registro_id,
            tipo_documento=dados.get("tipo_documento"),
            dados_extraidos=dados,
            tempo_processamento=tempo,
            modelo_openai=extracao.get("modelo"),
            tokens_entrada=extracao.get("tokens_entrada"),
            tokens_saida=extracao.get("tokens_saida"),
            custo_estimado=extracao.get("custo_estimado"),
        )

        # 16. Mover/excluir arquivo original
        _mover_processado(caminho)

        resultado["status"] = "sucesso"
        resultado["dados"] = dados
        resultado["tempo"] = tempo

        log.info(
            f"OK | {caminho.name} | tipo={dados.get('tipo_documento')} "
            f"| valor={dados.get('valor')} | direcao={direcao} | {tempo:.1f}s"
        )

        return resultado

    except Exception as exc:
        tempo = time.time() - inicio
        resultado["erro"] = f"{type(exc).__name__}: {exc}"
        resultado["tempo"] = tempo
        log.error(f"Erro ao processar {caminho.name}: {exc}", exc_info=True)

        try:
            hash_md5_err = calcular_md5(caminho) if caminho.exists() else "desconhecido"
            _mover_para_falhas(caminho, str(exc), resultado.get("dados"), hash_md5_err)
        except Exception:
            pass

        return resultado


def _mover_processado(caminho: Path) -> None:
    """Move arquivo para pasta de processados ou exclui conforme configuracao."""
    try:
        if DELETE_PROCESSED_FILES:
            caminho.unlink()
            log.info(f"Arquivo excluido: {caminho.name}")
        else:
            destino = mover_arquivo(caminho, PROCESSADOS_PATH)
            log.info(f"Arquivo movido para processados: {destino.name}")
    except Exception as exc:
        log.error(f"Erro ao mover/excluir arquivo {caminho.name}: {exc}")


def _mover_para_falhas(
    caminho: Path,
    erro: str,
    dados_parciais: dict | None,
    hash_md5: str,
) -> None:
    """Move arquivo para pasta de falhas e cria JSON de diagnostico."""
    try:
        if not caminho.exists():
            return

        destino = mover_arquivo(caminho, FALHAS_PATH)

        # JSON de diagnostico
        diag = {
            "arquivo": caminho.name,
            "hash_md5": hash_md5,
            "etapa": "processamento",
            "erro": erro,
            "stack_trace": traceback.format_exc(),
            "dados_parciais": dados_parciais,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        diag_path = destino.with_suffix(".json")
        diag_path.write_text(json.dumps(diag, ensure_ascii=False, indent=2), encoding="utf-8")

        log.info(f"Arquivo movido para falhas: {destino.name}")
    except Exception as exc:
        log.error(f"Erro ao mover para falhas {caminho.name}: {exc}")


# ============================================================
# WATCHDOG EVENT HANDLER
# ============================================================

class DocumentHandler(FileSystemEventHandler):
    """Handler para novos arquivos detectados pelo watchdog."""

    def __init__(self, executor: ProcessPoolExecutor):
        super().__init__()
        self._executor = executor
        self._pending: set[str] = set()

    def on_created(self, event):
        if event.is_directory:
            return
        self._handle(Path(event.src_path))

    def on_moved(self, event):
        if event.is_directory:
            return
        self._handle(Path(event.dest_path))

    def _handle(self, caminho: Path) -> None:
        """Submete arquivo para processamento se for suportado."""
        if not extensao_suportada(caminho):
            return

        caminho_str = str(caminho.resolve())
        if caminho_str in self._pending:
            return
        self._pending.add(caminho_str)

        log.info(f"Novo arquivo detectado: {caminho.name}")

        future = self._executor.submit(processar_arquivo, caminho_str)
        future.add_done_callback(lambda f: self._on_done(f, caminho_str))

    def _on_done(self, future: Future, caminho_str: str) -> None:
        """Callback executado quando o processamento termina."""
        self._pending.discard(caminho_str)
        try:
            resultado = future.result()
            status = resultado["status"]
            if status == "sucesso":
                log.info(f"Pipeline concluido: {resultado['arquivo']} ({resultado['tempo']:.1f}s)")
            elif status == "duplicado":
                log.info(f"Duplicado ignorado: {resultado['arquivo']}")
            else:
                log.warning(f"Pipeline com falha: {resultado['arquivo']} - {resultado.get('erro')}")
        except Exception as exc:
            log.error(f"Erro no worker: {exc}", exc_info=True)


# ============================================================
# PROCESSAR ARQUIVOS EXISTENTES NA INICIALIZACAO
# ============================================================

def processar_existentes(executor: ProcessPoolExecutor) -> None:
    """Processa arquivos que ja estao na pasta de entrada ao iniciar."""
    arquivos = [
        f for f in ENTRADA_PATH.iterdir()
        if f.is_file() and extensao_suportada(f)
    ]
    if not arquivos:
        log.info("Nenhum arquivo existente na pasta de entrada.")
        return

    log.info(f"Processando {len(arquivos)} arquivo(s) existente(s)...")
    futures: list[tuple[Future, Path]] = []
    for arq in arquivos:
        future = executor.submit(processar_arquivo, str(arq.resolve()))
        futures.append((future, arq))

    for future, arq in futures:
        try:
            resultado = future.result(timeout=300)
            log.info(f"Existente: {arq.name} -> {resultado['status']} ({resultado.get('tempo', 0):.1f}s)")
        except Exception as exc:
            log.error(f"Erro ao processar existente {arq.name}: {exc}")


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """Ponto de entrada principal do sistema de monitoramento."""
    log.info("=" * 60)
    log.info("SISTEMA OCR + IA + RPA - Iniciando...")
    log.info("=" * 60)

    # Inicializar banco de dados
    inicializar_banco()

    # Criar executor de processos
    executor = ProcessPoolExecutor(max_workers=MAX_WORKERS)

    # Processar arquivos ja existentes
    processar_existentes(executor)

    # Configurar watchdog
    handler = DocumentHandler(executor)
    observer = Observer()

    # Monitorar pasta de entrada
    observer.schedule(handler, str(ENTRADA_PATH), recursive=False)
    log.info(f"Monitorando: {ENTRADA_PATH}")

    # Monitorar pasta do WhatsApp (se existir)
    if WHATSAPP_PATH and WHATSAPP_PATH.exists():
        observer.schedule(handler, str(WHATSAPP_PATH), recursive=False)
        log.info(f"Monitorando WhatsApp: {WHATSAPP_PATH}")
    elif WHATSAPP_PATH:
        log.warning(f"Pasta do WhatsApp nao encontrada: {WHATSAPP_PATH}")

    observer.start()

    # Shutdown gracioso
    def _signal_handler(sig, frame):
        log.info(f"Sinal de shutdown recebido ({sig}). Finalizando...")
        _shutdown.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    log.info("Sistema pronto. Aguardando novos arquivos... (Ctrl+C para sair)")

    try:
        while not _shutdown.is_set():
            _shutdown.wait(timeout=1.0)
    except KeyboardInterrupt:
        pass
    finally:
        log.info("Finalizando sistema...")
        observer.stop()
        observer.join(timeout=5)
        executor.shutdown(wait=True, cancel_futures=True)
        log.info("Sistema finalizado.")


if __name__ == "__main__":
    main()