from pathlib import Path


def resolve_path(base : str | Path, path: str | Path):
    path = Path(path)
    if path.is_absolute():
        return path.resolve()
    return Path(base).resolve() / path

def is_binary_file(path : str | Path) -> bool:
    try:
        with open(path, 'rb') as f:
            chunk = f.read(8192)
            return b"\x00" in chunk
    except (OSError, IOError) as e:
        return False
    except Exception as e:
        return False
    

def display_path_rel_to_cwd(path: str, cwd: str) -> str:
    try:
        _resolve_base_path =  Path(path)
    except Exception as e:
        return path

    if cwd:
        try:
            return str(_resolve_base_path.relative_to(cwd))
        except Exception as e:
            pass 
    return str(_resolve_base_path)