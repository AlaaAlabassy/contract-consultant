"""Stubs heavy optional deps (chromadb, sentence-transformers) when they are
not installed - e.g. running unit tests on a machine that only has the
lightweight deps (pydantic-settings, httpx) and not the full torch/chromadb
stack from requirements.txt. In Codespaces, where the real packages are
installed, this is a no-op.
"""

import sys
import types


def _stub(name: str, **attrs: object) -> None:
    try:
        __import__(name)
    except ImportError:
        module = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(module, key, value)
        sys.modules[name] = module


_stub("sentence_transformers", SentenceTransformer=object)
_stub("chromadb", HttpClient=lambda *a, **k: None, ClientAPI=object)
