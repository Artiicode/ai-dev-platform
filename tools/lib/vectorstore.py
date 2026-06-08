"""vectorstore — sqlite-vec 기반 로컬 벡터 스토어 (RAG).

단일 파일 DB(info/vector/store.db). 의존성 최소(sqlite-vec). 메타데이터는 일반 테이블,
임베딩은 vec0 가상 테이블에 둔다. 같은 rowid 로 조인.
"""
from __future__ import annotations
import os
import sqlite3
from typing import List, Optional, Tuple

import sqlite_vec

__tool_version__ = "0.1.0"


class VectorStore:
    def __init__(self, db_path: str, dim: int):
        self.dim = dim
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.enable_load_extension(True)
        sqlite_vec.load(self.db)
        self.db.enable_load_extension(False)
        self._init_schema()

    def _init_schema(self):
        self.db.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(embedding float[{self.dim}])"
        )
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS chunks(
                   rowid     INTEGER PRIMARY KEY,
                   doc_id    TEXT NOT NULL,
                   chunk_idx INTEGER NOT NULL,
                   text      TEXT NOT NULL,
                   source    TEXT NOT NULL
               )"""
        )
        self.db.commit()

    def delete_doc(self, doc_id: str):
        """멱등 재인제스트: 같은 doc_id 기존 청크 제거 후 재삽입."""
        rows = self.db.execute("SELECT rowid FROM chunks WHERE doc_id=?", (doc_id,)).fetchall()
        for (rid,) in rows:
            self.db.execute("DELETE FROM chunks_vec WHERE rowid=?", (rid,))
        self.db.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        self.db.commit()

    def add_chunks(self, doc_id: str, source: str, texts: List[str], vecs: List[List[float]]):
        self.delete_doc(doc_id)
        cur = self.db.execute("SELECT COALESCE(MAX(rowid),0) FROM chunks")
        rid = cur.fetchone()[0]
        for i, (t, v) in enumerate(zip(texts, vecs)):
            rid += 1
            self.db.execute(
                "INSERT INTO chunks(rowid, doc_id, chunk_idx, text, source) VALUES (?,?,?,?,?)",
                (rid, doc_id, i, t, source),
            )
            self.db.execute(
                "INSERT INTO chunks_vec(rowid, embedding) VALUES (?, ?)",
                (rid, sqlite_vec.serialize_float32(v)),
            )
        self.db.commit()

    def search(self, query_vec: List[float], k: int = 5) -> List[dict]:
        rows = self.db.execute(
            """SELECT v.distance, c.doc_id, c.chunk_idx, c.text, c.source
                   FROM chunks_vec v JOIN chunks c ON c.rowid = v.rowid
                   WHERE v.embedding MATCH ? AND k = ?
                   ORDER BY v.distance""",
            (sqlite_vec.serialize_float32(query_vec), k),
        ).fetchall()
        return [
            {"distance": d, "doc_id": did, "chunk_idx": ci, "text": txt, "source": src}
            for (d, did, ci, txt, src) in rows
        ]

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    def close(self):
        self.db.close()


def chunk_text(text: str, size: int = 1200, overlap: int = 150) -> List[str]:
    """문자 기반 슬라이딩 청크. 단순·결정적. (토큰 기반 고도화는 추후)"""
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    out, start = [], 0
    while start < len(text):
        out.append(text[start:start + size])
        start += size - overlap
    return out
