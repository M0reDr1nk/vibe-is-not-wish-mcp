"""Gate utilities — confirmation blocks embedded in documents."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from ..store.project import Project


class GateManager:
    """Manage confirmation blocks inside layer documents."""

    def __init__(self, project: Project):
        self.project = project

    def embed_confirmation(
        self,
        layer: str,
        doc_file: str,
        item_type: str,
        description: str,
        cfm_id: str,
        blocking: bool = True,
    ) -> None:
        """Append a confirmation block to a layer document."""
        path = self.project.get_layer_dir(layer) / doc_file
        if not path.exists():
            raise FileNotFoundError(f"{layer}/{doc_file} not found")

        block = f"""

## [待确认] {item_type}

{description}

> [!IMPORTANT]
> **请确认上述内容**
>
> 确认ID: `{cfm_id}`  
> 阻塞流转: {'是' if blocking else '否'}  
> 提出时间: {datetime.utcnow().isoformat()}  
> 可选操作: approve / reject / modify
>
> <!-- 确认后在此追加：
> 确认结果: ___  
> 确认时间: ___  
> 确认人: ___
> -->

"""
        content = path.read_text(encoding="utf-8")
        path.write_text(content + block, encoding="utf-8")

    def scan_unresolved_blocks(self, layer: str) -> list[dict[str, Any]]:
        """Scan a layer's README for unresolved confirmation blocks."""
        path = self.project.get_layer_dir(layer) / "README.md"
        if not path.exists():
            return []

        content = path.read_text(encoding="utf-8")
        # Match [待确认] sections without a filled 确认结果
        pattern = re.compile(
            r"## \[待确认\] .*?\n.*?确认ID: `(.+?)`.*?阻塞流转: (.+?)\n",
            re.DOTALL,
        )
        unresolved = []
        for m in pattern.finditer(content):
            cfm_id = m.group(1)
            # Check if this block already has a resolution line
            block_end = content.find("\n## ", m.end())
            block = content[m.start() : block_end if block_end != -1 else None]
            if "确认结果:" not in block or "___" in block.split("确认结果:")[1][:20]:
                unresolved.append({
                    "cfm_id": cfm_id,
                    "blocking": "是" in m.group(2),
                    "layer": layer,
                })
        return unresolved
