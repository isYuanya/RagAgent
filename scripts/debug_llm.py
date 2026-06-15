from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.core.llm import get_llm_client


def main() -> int:
    prompt = " ".join(sys.argv[1:]).strip() or "用一句话解释RAG"

    print(f"OPENAI_BASE_URL={settings.openai_base_url}")
    print(f"OPENAI_MODEL={settings.openai_model}")
    print("PROMPT=" + prompt)
    print()

    response = get_llm_client().complete(prompt)
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
