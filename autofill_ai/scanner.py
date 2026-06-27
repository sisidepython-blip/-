"""模块1: 本地文件感知器 - 扫描资料文件夹，收集所有可用的个人资料文件。"""

from pathlib import Path

SUPPORTED_EXTENSIONS = {".txt", ".json", ".csv", ".md"}


def scan_folder(folder_path: str) -> dict:
    """扫描指定文件夹，返回分类后的文件列表。"""
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"文件夹不存在: {folder_path}")

    result = {
        "profile_files": [],
        "json_files": [],
        "image_files": [],
        "other_files": [],
    }

    for f in folder.iterdir():
        if f.is_file():
            suffix = f.suffix.lower()
            if suffix in {".txt", ".md"}:
                result["profile_files"].append(f)
            elif suffix == ".json":
                result["json_files"].append(f)
            elif suffix in {".png", ".jpg", ".jpeg"}:
                result["image_files"].append(f)
            else:
                result["other_files"].append(f)

    return result


def find_files(folder_path: str, patterns: list[str]) -> list[Path]:
    """在文件夹中查找匹配特定模式的文件。"""
    folder = Path(folder_path)
    found = []
    for pattern in patterns:
        found.extend(folder.glob(pattern))
    return sorted(found)
