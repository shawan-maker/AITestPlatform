"""本地 RAG 诊断脚本。用法: python scripts/diag_rag.py"""
import asyncio
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def main() -> None:
    from service.knowledge.pipeline.rag_gateway import RagGateway

    print("=== RAG 诊断 ===")
    print("remote_available:", RagGateway.is_remote_available())

    try:
        from rag.ragManager import RAGManager  # noqa: F401

        print("RAGManager import: OK")
    except Exception as exc:
        print("RAGManager import FAIL:", type(exc).__name__, exc)
        return

    td = tempfile.mkdtemp()
    test_file = Path(td) / "test.md"
    test_file.write_text("# hello\nworld", encoding="utf-8")

    try:
        backend, doc_id = await RagGateway.index_text(
            workspace_key="_diag_test",
            absolute_path=str(test_file),
            doc_id="diag/1",
        )
        print("index_text OK:", backend, doc_id)
    except Exception as exc:
        print("index_text FAIL:", type(exc).__name__, exc)
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
