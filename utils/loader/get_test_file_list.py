import mimetypes
import os
from typing import List, Dict


def get_file_type(file_path: str) -> str:
    """
    获取文件类型
    Args:
        file_path: 文件路径
    Returns:
        str: 文件类型描述
    """
    # 初始化mimetypes
    mimetypes.init()
    # 获取MIME类型
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        # 如果无法检测到MIME类型，则返回文件扩展名
        ext = os.path.splitext(file_path)[1][1:].lower()
        return ext if ext else "unknown"
    return mime_type


def inspect_env_data() -> Dict:
    """
    获取data/files目录下的文件信息
    Returns:
        List[Dict]: 包含文件名、文件路径和文件类型的列表
    """
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    file_dir = os.path.join(current_dir, 'test_data', 'files')

    # 确保目录存在
    if not os.path.exists(file_dir):
        os.makedirs(file_dir, exist_ok=True)
        return {"files": {}}

    # 构建目标格式的字典
    files_dict = {}
    index = 1

    for file_name in os.listdir(file_dir):
        file_path = os.path.join(file_dir, file_name)
        if os.path.isfile(file_path):  # 只处理文件，不处理子目录
            file_key = f"file{index}"
            files_dict[file_key] = {
                "path": file_path,
                "name": file_name,
                "type": get_file_type(file_path)
            }
            index += 1

    return {"files": files_dict}


if __name__ == '__main__':
    import json

    result = inspect_env_data()
    print(json.dumps(result, ensure_ascii=False, indent=4))