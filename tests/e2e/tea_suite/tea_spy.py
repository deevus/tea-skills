from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import stat


@dataclass(frozen=True)
class TeaSpy:
    bin_dir: Path
    audit_log: Path
    real_tea: Path

    @property
    def path_prefix(self) -> str:
        return str(self.bin_dir)


def create_tea_spy(root: Path, real_tea: Path, audit_log: Path) -> TeaSpy:
    bin_dir = root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "tea"
    wrapper.write_text(
        f'''#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

real = {str(real_tea)!r}
audit = Path({str(audit_log)!r})
argv = sys.argv[1:]
proc = subprocess.run([real] + argv, text=False)
event = {{
    "source": "tea",
    "argv": argv,
    "cwd": os.getcwd(),
    "pid": os.getpid(),
    "phase": "finish",
    "exit_code": proc.returncode,
    "timestamp": datetime.now(timezone.utc).isoformat(),
}}
audit.parent.mkdir(parents=True, exist_ok=True)
with audit.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(event, sort_keys=True) + "\\n")
raise SystemExit(proc.returncode)
''',
        encoding="utf-8",
    )
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return TeaSpy(bin_dir=bin_dir, audit_log=audit_log, real_tea=real_tea)
