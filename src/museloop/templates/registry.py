"""Template registry — discovers YAML templates from builtin directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from museloop.templates.base import ExportSettings, TemplateStep, WorkflowTemplate
from museloop.utils.logging import get_logger

logger = get_logger(__name__)

_BUILTIN_DIR = Path(__file__).parent / "builtin"


class TemplateRegistry:
    """Discovers and manages workflow templates."""

    def __init__(self) -> None:
        self._templates: dict[str, WorkflowTemplate] = {}

    def discover(self, templates_dir: str | Path | None = None) -> None:
        """Load templates from YAML files in the templates directory."""
        try:
            import yaml
        except ImportError:
            logger.warning("pyyaml_not_installed", msg="Install pyyaml for template support")
            return

        search_dir = Path(templates_dir) if templates_dir else _BUILTIN_DIR
        if not search_dir.exists():
            logger.warning("templates_dir_not_found", path=str(search_dir))
            return

        for template_file in sorted(search_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(template_file.read_text())
                template = self._parse_template(data)
                self._templates[template.name] = template
                logger.info("template_loaded", name=template.name)
            except Exception as e:
                logger.warning(
                    "template_load_failed",
                    file=template_file.name,
                    error=str(e),
                )

    def _parse_template(self, data: dict[str, Any]) -> WorkflowTemplate:
        """Parse a template dict into a WorkflowTemplate model."""
        steps = [
            TemplateStep(**step)
            for step in data.get("steps", [])
        ]
        export_data = data.get("export", {})
        export = ExportSettings(**export_data) if export_data else ExportSettings()

        duration = data.get("duration_range", [30, 60])
        if isinstance(duration, list) and len(duration) == 2:
            duration_range = (duration[0], duration[1])
        else:
            duration_range = (30, 60)

        return WorkflowTemplate(
            name=data["name"],
            category=data.get("category", "general"),
            description=data.get("description", ""),
            default_style=data.get("default_style", ""),
            default_skills=data.get("default_skills", []),
            steps=steps,
            export=export,
            duration_range=duration_range,
            constraints=data.get("constraints", {}),
        )

    def register(self, template: WorkflowTemplate) -> None:
        """Manually register a template."""
        self._templates[template.name] = template

    def get(self, name: str) -> WorkflowTemplate:
        """Get a template by name."""
        if name not in self._templates:
            raise KeyError(
                f"Template '{name}' not found. Available: {list(self._templates.keys())}"
            )
        return self._templates[name]

    def has(self, name: str) -> bool:
        return name in self._templates

    def list_templates(self) -> list[str]:
        return list(self._templates.keys())

    def list_details(self) -> list[dict[str, str]]:
        return [
            {
                "name": t.name,
                "category": t.category,
                "description": t.description,
            }
            for t in self._templates.values()
        ]
