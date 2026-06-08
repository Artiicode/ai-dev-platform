"""llm — 모델/프로바이더 비종속 추론 실행층 (LiteLLM 기반). 강제성 ③.

원칙(사용자 확정): 의존성 0이 기본. **API_KEY가 환경에 있거나 유저가 모델을 명시할 때만**
해당 모델/프로바이더 의존성이 붙는다. 논리적 역할(planner/coder/verifier/embedder)은
platform/models/models.yaml 에서 읽어 LiteLLM 모델 문자열(`<provider>/<model>`)로 해석한다.

- 키 없음 → 해당 역할은 '비활성'(명확한 에러). 파이프라인이 임의 프로바이더로 폴백하지 않는다.
- litellm 미설치 → 'pip install litellm' 안내(평소엔 import 안 하므로 의존성 0 유지).
- provider: local (임베딩 등)은 키 불필요 — embedder.py 가 별도 처리.
"""
from __future__ import annotations
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tools/lib/ → 플랫폼 루트
MODELS_YAML = os.path.join(ROOT, "platform", "models", "models.yaml")

__tool_version__ = "0.1.0"


def load_models() -> dict:
    import yaml
    with open(MODELS_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_role(role: str):
    """role → (provider, model, api_key_env). 없는 role 이면 KeyError."""
    roles = load_models().get("roles", {})
    if role not in roles:
        raise KeyError("models.yaml 에 role '%s' 없음 (가능: %s)" % (role, ", ".join(roles)))
    cfg = roles[role] or {}
    return cfg.get("provider"), cfg.get("model"), cfg.get("api_key_env")


def litellm_model_id(provider: str, model: str):
    """LiteLLM 모델 문자열. 이미 'prov/model' 이면 그대로. local 이면 None."""
    if not provider or provider == "local":
        return None
    return model if (model and "/" in model) else "%s/%s" % (provider, model)


def role_available(role: str) -> bool:
    """네트워크 없이 가용성 판정. local 이거나 키 env 가 채워져 있으면 True."""
    provider, _, key_env = resolve_role(role)
    if provider == "local":
        return True
    return bool(key_env and os.environ.get(key_env))


def complete(role: str, messages, **kwargs):
    """역할로 추론 실행. 키 없으면 RuntimeError, litellm 없으면 안내 에러."""
    provider, model, key_env = resolve_role(role)
    if provider == "local":
        raise RuntimeError("role '%s' 는 local provider — 추론 호출 대상이 아닙니다." % role)
    if key_env and not os.environ.get(key_env):
        raise RuntimeError(
            "role '%s' 비활성: 환경변수 %s 미설정. 키를 .env 에 넣거나 models.yaml 을 바꾸세요."
            % (role, key_env))
    try:
        import litellm  # 평소엔 import 안 함 → 의존성 0 유지
    except ImportError:
        raise RuntimeError("litellm 미설치: pip install litellm (멀티프로바이더 실행층).")
    mid = litellm_model_id(provider, model)
    return litellm.completion(model=mid, messages=messages, **kwargs)


def audit() -> int:
    """`harness models` — 네트워크 없이 역할별 가용성 점검."""
    m = load_models()
    roles = m.get("roles", {})
    if not roles:
        print("[models] models.yaml 에 roles 가 없습니다."); return 1
    print("[models] %s" % MODELS_YAML)
    try:
        import litellm  # noqa: F401
        lit = "litellm 설치됨"
    except ImportError:
        lit = "litellm 미설치(추론 시 필요: pip install litellm)"
    print("         %s" % lit)
    for role, cfg in roles.items():
        cfg = cfg or {}
        prov, model, key_env = cfg.get("provider"), cfg.get("model"), cfg.get("api_key_env")
        if prov == "local":
            status = "OK — 로컬(키 불필요)"
        elif not key_env:
            status = "⚠ api_key_env 미지정"
        elif os.environ.get(key_env):
            status = "OK — %s 설정됨" % key_env
        else:
            status = "비활성 — %s 없음" % key_env
        mid = litellm_model_id(prov, model) or ("%s:%s" % (prov, model))
        print("  %-9s %-28s %s" % (role, mid, status))
    return 0


if __name__ == "__main__":
    sys.exit(audit())
