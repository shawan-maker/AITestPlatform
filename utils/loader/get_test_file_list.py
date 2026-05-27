import mimetypes
import os
from typing import Any, Dict


def get_file_type(file_path: str) -> str:
    """获取文件 MIME 类型或扩展名。"""
    mimetypes.init()
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        ext = os.path.splitext(file_path)[1][1:].lower()
        return ext if ext else "unknown"
    return mime_type


def _files_from_test_env_data(test_env_data: dict[str, Any]) -> Dict:
    raw = test_env_data.get("files")
    if isinstance(raw, dict) and raw:
        return {"files": raw}
    return {"files": {}}


def _files_from_demo_dir() -> Dict:
    """仅 inspect_env_data() 无参调用时使用（__main__ / 本地 demo）。"""
    from service.core.config import AI_DEMO_FILES_DIR

    file_dir = str(AI_DEMO_FILES_DIR)
    if not os.path.isdir(file_dir):
        return {"files": {}}

    files_dict: dict[str, dict] = {}
    index = 1
    for file_name in os.listdir(file_dir):
        file_path = os.path.join(file_dir, file_name)
        if os.path.isfile(file_path):
            files_dict[f"file{index}"] = {
                "path": file_path,
                "name": file_name,
                "type": get_file_type(file_path),
            }
            index += 1
    return {"files": files_dict}


def inspect_env_data(test_env_data: dict[str, Any] | None = None) -> Dict:
    """
    获取测试文件列表。
    生产路径传入 test_env_data（来自 TestEnvDataAssembler）；无参时读配置目录（demo）。
    """
    if test_env_data:
        return _files_from_test_env_data(test_env_data)
    return _files_from_demo_dir()


if __name__ == "__main__":
    import json

    result = inspect_env_data()
    print(json.dumps(result, ensure_ascii=False, indent=4))
