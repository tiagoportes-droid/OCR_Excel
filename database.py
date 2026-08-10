"""
Gerenciamento do banco SQLite para registro de processamentos.
"""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from config import DATABASE_PATH
from logger import log

_db_lock = threading.Lock()


def _get_connection() -> sqlite3.Connection:
    """Cria conexao com o banco (por thread/processo)."""
    conn = sqlite3.connect(str(DATABASE_PATH), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_banco() -> None:
    """Cria as tabelas se nao existirem."""
    with _db_lock:
        conn = _get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processamentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash_md5 TEXT NOT NULL,
                    nome_arquivo TEXT NOT NULL,
                    caminho TEXT,
                    tipo_documento TEXT,
                    status TEXT NOT NULL DEFAULT 'pendente',
                    data TEXT,
                    hora TEXT,
                    tempo_processamento REAL,
                    dados_extraidos TEXT,
                    erro TEXT,
                    tentativas INTEGER DEFAULT 0,
                    modelo_openai TEXT,
                    tokens_entrada INTEGER,
                    tokens_saida INTEGER,
                    custo_estimado REAL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_hash ON processamentos(hash_md5)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON processamentos(status)
            """)
            conn.commit()
        finally:
            conn.close()


def hash_ja_processado(hash_md5: str) -> bool:
    """Verifica se o hash ja foi processado com sucesso."""
    with _db_lock:
        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT status FROM processamentos WHERE hash_md5 = ? AND status = 'sucesso' LIMIT 1",
                (hash_md5,),
            ).fetchone()
            return row is not None
        finally:
            conn.close()


def hash_falhou(hash_md5: str) -> bool:
    """Verifica se o hash falhou (permitir reprocessamento)."""
    with _db_lock:
        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT status FROM processamentos WHERE hash_md5 = ? AND status = 'falha' LIMIT 1",
                (hash_md5,),
            ).fetchone()
            return row is not None
        finally:
            conn.close()


def registrar_inicio(
    hash_md5: str,
    nome_arquivo: str,
    caminho: str,
) -> int:
    """Registra o inicio do processamento. Retorna o ID do registro."""
    with _db_lock:
        conn = _get_connection()
        try:
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor = conn.execute(
                """
                INSERT INTO processamentos (hash_md5, nome_arquivo, caminho, status, data, hora, tentativas, created_at, updated_at)
                VALUES (?, ?, ?, 'processando', ?, ?, 1, ?, ?)
                """,
                (
                    hash_md5,
                    nome_arquivo,
                    caminho,
                    datetime.now().strftime("%Y-%m-%d"),
                    datetime.now().strftime("%H:%M:%S"),
                    agora,
                    agora,
                ),
            )
            conn.commit()
            return cursor.lastrowid  # type: ignore[return-value]
        finally:
            conn.close()


def registrar_sucesso(
    registro_id: int,
    tipo_documento: str | None = None,
    dados_extraidos: dict[str, Any] | None = None,
    tempo_processamento: float | None = None,
    modelo_openai: str | None = None,
    tokens_entrada: int | None = None,
    tokens_saida: int | None = None,
    custo_estimado: float | None = None,
) -> None:
    """Registra processamento concluido com sucesso."""
    with _db_lock:
        conn = _get_connection()
        try:
            dados_json = json.dumps(dados_extraidos, ensure_ascii=False, default=str) if dados_extraidos else None
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """
                UPDATE processamentos
                SET status = 'sucesso',
                    tipo_documento = ?,
                    dados_extraidos = ?,
                    tempo_processamento = ?,
                    modelo_openai = ?,
                    tokens_entrada = ?,
                    tokens_saida = ?,
                    custo_estimado = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    tipo_documento,
                    dados_json,
                    tempo_processamento,
                    modelo_openai,
                    tokens_entrada,
                    tokens_saida,
                    custo_estimado,
                    agora,
                    registro_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def registrar_falha(
    registro_id: int,
    erro: str,
    dados_parciais: dict[str, Any] | None = None,
    tempo_processamento: float | None = None,
    modelo_openai: str | None = None,
    tokens_entrada: int | None = None,
    tokens_saida: int | None = None,
    custo_estimado: float | None = None,
) -> None:
    """Registra falha no processamento."""
    with _db_lock:
        conn = _get_connection()
        try:
            dados_json = json.dumps(dados_parciais, ensure_ascii=False, default=str) if dados_parciais else None
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """
                UPDATE processamentos
                SET status = 'falha',
                    erro = ?,
                    dados_extraidos = ?,
                    tempo_processamento = ?,
                    modelo_openai = ?,
                    tokens_entrada = ?,
                    tokens_saida = ?,
                    custo_estimado = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    erro[:2000] if erro else None,
                    dados_json,
                    tempo_processamento,
                    modelo_openai,
                    tokens_entrada,
                    tokens_saida,
                    custo_estimado,
                    agora,
                    registro_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def obter_estatisticas() -> dict[str, Any]:
    """Retorna estatisticas gerais do banco."""
    with _db_lock:
        conn = _get_connection()
        try:
            total = conn.execute("SELECT COUNT(*) FROM processamentos").fetchone()[0]
            sucesso = conn.execute("SELECT COUNT(*) FROM processamentos WHERE status='sucesso'").fetchone()[0]
            falha = conn.execute("SELECT COUNT(*) FROM processamentos WHERE status='falha'").fetchone()[0]
            processando = conn.execute("SELECT COUNT(*) FROM processamentos WHERE status='processando'").fetchone()[0]
            custo_total_row = conn.execute(
                "SELECT COALESCE(SUM(custo_estimado), 0) FROM processamentos WHERE status='sucesso'"
            ).fetchone()
            custo_total = custo_total_row[0] if custo_total_row else 0.0
            return {
                "total": total,
                "sucesso": sucesso,
                "falha": falha,
                "processando": processando,
                "custo_total": custo_total,
            }
        finally:
            conn.close()


# Inicializar banco na importacao
inicializar_banco()