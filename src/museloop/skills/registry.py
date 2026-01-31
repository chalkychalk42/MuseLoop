"""Skill registry — discovers and loads skills from manifests."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

from museloop.skills.base import BaseSkill
from museloop.utils.logging import get_logger

logger = get_logger(__name__)

# Default manifests directory (relative to this file)
_MANIFESTS_DIR = Path(__file__).parent / "manifests"


class SkillRegistry:
    """Discovers and loads skills from the manifests directory."""

    def __init__(self, skill_config: dict[str, Any] | None = None) -> None:
        self._skills: dict[str, BaseSkill] = {}
        self._skill_config = skill_config or {}

    def discover(self, manifests_dir: str | Path | None = None) -> None:
        """Scan manifests directory for JSON files and load corresponding skills."""
        search_dir = Path(manifests_dir) if manifests_dir else _MANIFESTS_DIR
        if not search_dir.exists():
            logger.warning("manifests_dir_not_found", path=str(search_dir))
            return

        for manifest_file in sorted(search_dir.glob("*.json")):
            try:
                manifest = json.loads(manifest_file.read_text())
                module_name = manifest["module"]
                class_name = manifest["class"]

                module = importlib.import_module(module_name)
                skill_class = getattr(module, class_name)

                # Pass config to skill constructors that accept keyword args
                skill = self._instantiate_skill(skill_class)
                self._skills[skill.name] = skill

                logger.info("skill_loaded", name=skill.name, module=module_name)
            except Exception as e:
                logger.warning(
                    "skill_load_failed",
                    manifest=manifest_file.name,
                    error=str(e),
                )

    def _instantiate_skill(self, skill_class: type) -> BaseSkill:
        """Instantiate a skill, passing relevant config from skill_config."""
        import inspect

        sig = inspect.signature(skill_class.__init__)
        kwargs: dict[str, Any] = {}
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            if param_name in self._skill_config:
                kwargs[param_name] = self._skill_config[param_name]
        return skill_class(**kwargs)

    def register(self, skill: BaseSkill) -> None:
        """Manually register a skill instance."""
        self._skills[skill.name] = skill

    def get(self, name: str) -> BaseSkill:
        """Retrieve a skill by name."""
        if name not in self._skills:
            raise KeyError(
                f"Skill '{name}' not found. Available: {list(self._skills.keys())}"
            )
        return self._skills[name]

    def has(self, name: str) -> bool:
        """Check if a skill is registered."""
        return name in self._skills

    def list_skills(self) -> list[str]:
        """List all registered skill names."""
        return list(self._skills.keys())

    def list_details(self) -> list[dict[str, str]]:
        """List all skills with name and description."""
        return [
            {"name": s.name, "description": s.description}
            for s in self._skills.values()
        ]
