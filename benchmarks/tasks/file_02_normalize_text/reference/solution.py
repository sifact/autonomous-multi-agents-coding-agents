BOM = b"\xef\xbb\xbf"


def normalize_file(path: str) -> bool:
    with open(path, "rb") as f:
        raw = f.read()
    data = raw.removeprefix(BOM)
    data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    if data == raw:
        return False
    with open(path, "wb") as f:
        f.write(data)
    return True
