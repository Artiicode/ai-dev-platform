"""embedder — 로컬 우선 텍스트 임베딩.

기본 모델은 BAAI/bge-m3(sentence-transformers, 로컬/오프라인, dim=1024, 다국어·한국어 retrieval 우수).
대안: Qwen/Qwen3-Embedding-0.6B (instruction-tuned). 둘 다 1024차원이라 벡터스토어 드롭인.
(한국어 KorQuAD 실측에서 bge-m3 가 0.6B 보다 우수 — ADR 0011.)
모델 미설치 환경에서도 파이프라인이 동작하도록 결정적 'hash' 폴백 제공(테스트/오프라인용).
설정은 platform/models/models.yaml 의 embedding / HARNESS_EMBED_MODEL 를 따른다.

비대칭 인코딩: 문서(passage)는 plain, 쿼리는 `embed_query`(Qwen 류는 instruction 프리픽스 부착).
"""
from __future__ import annotations
import hashlib
import math
from typing import List

__tool_version__ = "0.2.0"

DEFAULT_DIM = 1024  # Qwen3-Embedding-0.6B / bge-m3 공통
DEFAULT_MODEL = "BAAI/bge-m3"
_QWEN_QUERY_INSTRUCT = "Instruct: Given a question, retrieve passages that answer it\nQuery: "


class HashEmbedder:
    """의존성 0, 결정적 임베더. 실제 의미가 아니라 토큰 해시 분포 기반(테스트/오프라인 폴백).

    같은 dim 을 유지해 스토어 스키마 호환을 보장한다. 정확한 의미 검색이 필요하면
    bge-m3 백엔드를 쓴다.
    """

    name = "hash"

    def __init__(self, dim: int = DEFAULT_DIM):
        self.dim = dim

    def _vec(self, text: str) -> List[float]:
        v = [0.0] * self.dim
        for tok in text.lower().split():
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            v[idx] += sign
        # L2 정규화 (코사인=내적이 되도록)
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed(self, texts: List[str]) -> List[List[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, texts: List[str]) -> List[List[float]]:
        return self.embed(texts)   # 해시 폴백은 비대칭 인코딩 없음


class SentenceTransformerEmbedder:
    """Qwen3-Embedding / bge-m3 등 로컬 임베딩 모델. sentence-transformers 필요(최초 1회 다운로드).

    문서는 plain 인코딩, 쿼리는 embed_query(Qwen 류는 instruction 프리픽스). bge-m3 는 프리픽스 없음.
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        from sentence_transformers import SentenceTransformer  # lazy import
        self._m = SentenceTransformer(model)
        self.name = model
        try:
            self.dim = self._m.get_embedding_dimension()
        except AttributeError:
            self.dim = self._m.get_sentence_embedding_dimension()
        # Qwen3-Embedding 류는 쿼리 instruction 으로 검색 품질이 크게 오른다(문서는 plain).
        self.query_instruction = _QWEN_QUERY_INSTRUCT if "qwen3-embedding" in model.lower() else None

    def embed(self, texts: List[str]) -> List[List[float]]:
        vecs = self._m.encode(texts, normalize_embeddings=True)
        return [list(map(float, v)) for v in vecs]

    def embed_query(self, texts: List[str]) -> List[List[float]]:
        if self.query_instruction:
            texts = [self.query_instruction + t for t in texts]
        return self.embed(texts)


def get_embedder(backend: str = "local", model: str = DEFAULT_MODEL,
                 dim: int = DEFAULT_DIM):
    """설정 → 임베더 인스턴스. 로컬 모델 로드 실패 시 hash 폴백으로 강등(경고 출력)."""
    if backend == "hash":
        return HashEmbedder(dim)
    try:
        return SentenceTransformerEmbedder(model)
    except Exception as e:  # 모델/라이브러리 부재 → 폴백
        import sys
        print(f"[embedder] '{model}' 로드 실패({type(e).__name__}) → hash 폴백 사용. "
              f"실검색용으로는 'pip install sentence-transformers' 후 모델 다운로드 필요.",
              file=sys.stderr)
        return HashEmbedder(dim)
