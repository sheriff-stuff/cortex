"""Template API routes."""

import asyncio

from fastapi import APIRouter, HTTPException

from api.config import Config
from api.db import MeetingRepository
from api.example_transcript import EXAMPLE_SEGMENTS
from api.extractor import extract_from_transcript
from api.llm import check_ollama
from api.prompts import EXTRACTION_SCHEMA
from api.responses import transform_items


def create_router(config: Config, repo: MeetingRepository) -> APIRouter:
    router = APIRouter(prefix="/api/templates")

    @router.get("")
    async def list_templates() -> list[dict]:
        """List all templates (without prompt_text)."""
        return repo.list_templates()

    @router.get("/{template_id}")
    async def get_template(template_id: int) -> dict:
        """Get a single template with full prompt_text and the locked schema."""
        tmpl = repo.get_template(template_id)
        if tmpl is None:
            raise HTTPException(status_code=404, detail="Template not found")
        tmpl["schema"] = EXTRACTION_SCHEMA
        return tmpl

    @router.post("", status_code=201)
    async def create_template(body: dict) -> dict:
        """Create a new template."""
        name = body.get("name", "").strip()
        description = body.get("description", "").strip()
        prompt_text = body.get("prompt_text", "")

        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        if not prompt_text:
            raise HTTPException(status_code=400, detail="prompt_text is required")
        new_id = repo.create_template(name, description, prompt_text)
        tmpl = repo.get_template(new_id)
        tmpl["schema"] = EXTRACTION_SCHEMA
        return tmpl

    @router.post("/render-example")
    async def render_example(body: dict) -> dict:
        """Run extraction on a hardcoded example transcript using the given prompt."""
        prompt_text = body.get("prompt_text", "").strip()
        if not prompt_text:
            raise HTTPException(status_code=400, detail="prompt_text is required")

        if not check_ollama(config):
            raise HTTPException(
                status_code=503,
                detail="Ollama is not available. Please ensure it is running.",
            )

        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: extract_from_transcript(
                    EXAMPLE_SEGMENTS, config, prompt_text=prompt_text,
                ),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"LLM extraction failed: {exc}",
            )

        return transform_items(
            result.topics, result.decisions,
            result.action_items, result.questions,
        )

    @router.put("/{template_id}")
    async def update_template(template_id: int, body: dict) -> dict:
        """Update an existing template. Cannot update the default template."""
        tmpl = repo.get_template(template_id)
        if tmpl is None:
            raise HTTPException(status_code=404, detail="Template not found")
        if tmpl["is_default"]:
            raise HTTPException(
                status_code=403, detail="Cannot edit the default template",
            )

        fields: dict = {}
        if "name" in body:
            name = body["name"].strip()
            if not name:
                raise HTTPException(status_code=400, detail="name cannot be empty")
            fields["name"] = name
        if "description" in body:
            fields["description"] = body["description"].strip()
        if "prompt_text" in body:
            fields["prompt_text"] = body["prompt_text"]

        if fields:
            repo.update_template(template_id, **fields)

        updated = repo.get_template(template_id)
        updated["schema"] = EXTRACTION_SCHEMA
        return updated

    @router.delete("/{template_id}", status_code=204)
    async def delete_template(template_id: int) -> None:
        """Delete a template. Cannot delete the default template."""
        tmpl = repo.get_template(template_id)
        if tmpl is None:
            raise HTTPException(status_code=404, detail="Template not found")
        if tmpl["is_default"]:
            raise HTTPException(
                status_code=403, detail="Cannot delete the default template",
            )
        repo.delete_template(template_id)

    @router.post("/{template_id}/duplicate", status_code=201)
    async def duplicate_template(template_id: int) -> dict:
        """Duplicate a template."""
        new_id = repo.duplicate_template(template_id)
        if new_id is None:
            raise HTTPException(status_code=404, detail="Template not found")
        tmpl = repo.get_template(new_id)
        tmpl["schema"] = EXTRACTION_SCHEMA
        return tmpl

    return router
