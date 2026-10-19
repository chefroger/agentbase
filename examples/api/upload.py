"""文件上传示例：上传到当前 workspace 的 work_dirs 子目录。

用法：
    python upload.py documents ./example.pdf
"""

from __future__ import annotations

import os
import sys

import requests

from _client import BASE, first_workspace, headers, json_print


def main() -> None:
    subdir = sys.argv[1] if len(sys.argv) > 1 else "documents"
    path = sys.argv[2] if len(sys.argv) > 2 else ""
    if not path or not os.path.isfile(path):
        raise SystemExit("用法：python upload.py <subdir> <file>")

    with open(path, "rb") as fh:
        resp = requests.post(
            f"{BASE}/api/agentbase/upload-files",
            headers=headers(first_workspace()),
            data={"subdir": subdir},
            files={"files": (os.path.basename(path), fh)},
            timeout=120,
        )
    resp.raise_for_status()
    json_print(resp.json())


if __name__ == "__main__":
    main()
