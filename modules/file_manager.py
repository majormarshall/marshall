"""
MARSHALL - File Manager Module
Full file system access: browse, read, search, open, delete, move.
"""
import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import mimetypes


def list_directory(path: str = "C:\\Users\\exboi marshall") -> Dict:
    """List contents of a directory."""
    try:
        p = Path(path)
        if not p.exists():
            return {"error": f"Path does not exist: {path}"}

        items = []
        for item in sorted(p.iterdir()):
            try:
                stat = item.stat()
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else None,
                    "modified": stat.st_mtime,
                    "extension": item.suffix.lower() if item.is_file() else None,
                })
            except (PermissionError, OSError):
                items.append({"name": item.name, "path": str(item), "type": "unknown", "error": "access denied"})

        return {
            "path": str(p),
            "parent": str(p.parent),
            "items": items,
            "count": len(items),
        }
    except Exception as e:
        return {"error": str(e)}


def search_files(query: str, search_path: str = "C:\\Users\\exboi marshall", extensions: Optional[List[str]] = None) -> Dict:
    """Search for files by name across the filesystem."""
    results = []
    query_lower = query.lower()

    try:
        for root, dirs, files in os.walk(search_path):
            # Skip system/hidden dirs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['$Recycle.Bin', 'Windows', 'System32']]
            for file in files:
                if query_lower in file.lower():
                    full_path = os.path.join(root, file)
                    ext = Path(file).suffix.lower()
                    if extensions is None or ext in extensions:
                        results.append({
                            "name": file,
                            "path": full_path,
                            "extension": ext,
                        })
                        if len(results) >= 100:
                            break
            if len(results) >= 100:
                break
    except Exception as e:
        return {"error": str(e), "results": results}

    return {"query": query, "results": results, "count": len(results)}


def read_file(file_path: str) -> Dict:
    """Read a text file's contents."""
    try:
        p = Path(file_path)
        if not p.exists():
            return {"error": "File not found"}
        if p.stat().st_size > 1_000_000:  # 1MB limit for reading
            return {"error": "File too large to read directly"}

        mime, _ = mimetypes.guess_type(file_path)
        if mime and not mime.startswith("text"):
            return {"error": f"Binary file ({mime}) - open with app instead"}

        content = p.read_text(encoding="utf-8", errors="replace")
        return {"path": file_path, "content": content, "lines": content.count("\n")}
    except Exception as e:
        return {"error": str(e)}


def delete_file(file_path: str) -> Dict:
    """Delete a file or empty directory."""
    try:
        p = Path(file_path)
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        return {"status": "deleted", "path": file_path}
    except Exception as e:
        return {"error": str(e)}


def move_file(src: str, dst: str) -> Dict:
    """Move or rename a file."""
    try:
        shutil.move(src, dst)
        return {"status": "moved", "from": src, "to": dst}
    except Exception as e:
        return {"error": str(e)}


def create_folder(path: str) -> Dict:
    """Create a new directory."""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return {"status": "created", "path": path}
    except Exception as e:
        return {"error": str(e)}


def get_drives() -> List[Dict]:
    """List available drives."""
    import string
    drives = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            try:
                total, used, free = shutil.disk_usage(drive)
                drives.append({
                    "drive": drive,
                    "total_gb": round(total / (1024**3), 2),
                    "used_gb": round(used / (1024**3), 2),
                    "free_gb": round(free / (1024**3), 2),
                })
            except Exception:
                drives.append({"drive": drive})
    return drives
