"""测试环境管理模块 - file/storage_backend

storage backend
"""
from abc import ABC, abstractmethod
from pathlib import Path

from service.core.settings import BASE_DIR


class StorageBackend(ABC):
    @abstractmethod
    def write(self, storage_key: str, content: bytes) -> None:
        ...

    @abstractmethod
    def absolute_path(self, storage_key: str) -> Path:
        ...

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        ...


class LocalStorageBackend(StorageBackend):
    def absolute_path(self, storage_key: str) -> Path:
        # 兼容 Windows 路径分隔符（DB 中可能存储反斜杠路径）
        return BASE_DIR / storage_key.replace("\\", "/")

    def write(self, storage_key: str, content: bytes) -> None:
        path = self.absolute_path(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def exists(self, storage_key: str) -> bool:
        return self.absolute_path(storage_key).exists()


_backend: StorageBackend | None = None


def get_storage_backend() -> StorageBackend:
    global _backend
    if _backend is None:
        _backend = LocalStorageBackend()
    return _backend
