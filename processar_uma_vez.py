"""
Processamento em lote (sem watchdog).

Procura todos os documentos em arquivos/entrada/, processa-os usando
o mesmo pipeline do sistema principal e finaliza automaticamente.

Uso:
  python processar_uma_vez.py
"""

from __future__ import annotations

import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from config import ENTRADA_PATH, MAX_WORKERS
from database import inicializar_banco, obter_estatisticas
from logger import log
from main import processar_arquivo
from utils import extensao_suportada, formatar_tempo


def main() -> None:
    """Executa o processamento em lote de todos os documentos na pasta de entrada."""
    log.info("=" * 60)
    log.info("PROCESSAMENTO EM LOTE - Iniciando...")
    log.info("=" * 60)

    inicio_total = time.time()

    # Inicializar banco
    inicializar_banco()

    # Listar arquivos suportados
    arquivos = sorted(
        f for f in ENTRADA_PATH.iterdir()
        if f.is_file() and extensao_suportada(f)
    )

    total_encontrados = len(arquivos)

    if total_encontrados == 0:
        log.info(f"Nenhum arquivo encontrado em {ENTRADA_PATH}")
        print(f"\nNenhum arquivo encontrado em {ENTRADA_PATH}")
        return

    log.info(f"Encontrados: {total_encontrados} arquivo(s)")
    print(f"\nEncontrados: {total_encontrados} arquivo(s)")
    print("-" * 40)

    # Contadores
    processados = 0
    falhas = 0
    duplicados = 0

    # Processar com pool de processos
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(processar_arquivo, str(arq.resolve())): arq
            for arq in arquivos
        }

        for future in as_completed(futures):
            arq = futures[future]
            try:
                resultado = future.result(timeout=300)
                status = resultado.get("status", "falha")

                if status == "sucesso":
                    processados += 1
                    print(f"  OK  {arq.name} ({resultado.get('tempo', 0):.1f}s)")
                elif status == "duplicado":
                    duplicados += 1
                    print(f"  DUP {arq.name} (duplicado)")
                else:
                    falhas += 1
                    print(f"  ERR {arq.name} - {resultado.get('erro', 'Erro desconhecido')}")

            except Exception as exc:
                falhas += 1
                print(f"  ERR {arq.name} - {type(exc).__name__}: {exc}")
                log.error(f"Erro ao processar {arq.name}: {exc}", exc_info=True)

    tempo_total = time.time() - inicio_total

    # Custo estimado
    try:
        stats = obter_estatisticas()
        custo_total = stats.get("custo_total", 0.0)
    except Exception:
        custo_total = 0.0

    # Resumo
    tempo_fmt = formatar_tempo(tempo_total)

    resumo = f"""
{'=' * 40}
RESUMO DO PROCESSAMENTO
{'=' * 40}
Encontrados:    {total_encontrados}
Processados:    {processados}
Falhas:         {falhas}
Duplicados:     {duplicados}
Tempo total:    {tempo_fmt}
Custo estimado: USD {custo_total:.4f}
{'=' * 40}
"""

    print(resumo)
    log.info(resumo.replace("\n", " | ").strip())


if __name__ == "__main__":
    main()