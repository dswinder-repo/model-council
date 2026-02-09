#!/usr/bin/env python3
"""
Model Council MCP Server

Fans out research queries to multiple frontier LLMs via OpenRouter,
returning structured responses for synthesis by the chairman (Harold/Claude).

Architecture:
  Query → Profile selection → Fan out to N models (concurrent) → Structured JSON
  Harold acts as "Chairman" — synthesizing with full knowledge base context.

Profiles auto-select the best models for the query type:
  strategic  → Opus 4.5 + o3 + Gemini 3 Pro (investment, GTM, positioning)
  technical  → Sonnet 4 + GPT-4.1 + DeepSeek R1 (product, architecture, code)
  research   → Opus 4.5 + GPT-4.1 + Gemini 3 Pro (market research, analysis)
  creative   → Opus 4.5 + GPT-4.1 + Gemini 3 Pro (content, messaging, naming)
  fast       → Sonnet 4 + GPT-4.1-mini + Gemini 3 Flash (quick validation)
  auto       → Harold picks the best profile based on query context (default)
"""

import os
import sys
import json
import asyncio
import re
from typing import Optional, List
from enum import Enum

import httpx
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


def _get_api_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "")


# ─────────────────────────────────────────────
# Model Profiles
# ─────────────────────────────────────────────

PROFILES = {
    "strategic": {
        "description": "Best reasoning engines for investment, strategy, GTM, positioning decisions",
        "models": [
            "anthropic/claude-opus-4-5",
            "openai/o3",
            "google/gemini-3-pro-preview",
        ],
    },
    "technical": {
        "description": "Strong on product, architecture, code, and technical analysis",
        "models": [
            "anthropic/claude-sonnet-4",
            "openai/gpt-4.1",
            "deepseek/deepseek-r1",
        ],
    },
    "research": {
        "description": "Broad knowledge for market research, competitive analysis, due diligence",
        "models": [
            "anthropic/claude-opus-4-5",
            "openai/gpt-4.1",
            "google/gemini-3-pro-preview",
        ],
    },
    "creative": {
        "description": "Content creation, messaging, naming, brand strategy",
        "models": [
            "anthropic/claude-opus-4-5",
            "openai/gpt-4.1",
            "google/gemini-3-pro-preview",
        ],
    },
    "fast": {
        "description": "Quick validation, fact-checking, simple comparisons",
        "models": [
            "anthropic/claude-sonnet-4",
            "openai/gpt-4.1-mini",
            "google/gemini-3-flash-preview",
        ],
    },
}

# Default profile for when Harold doesn't specify
DEFAULT_PROFILE = "research"

# Keywords that map to profiles (used by auto-classification)
PROFILE_SIGNALS = {
    "strategic": [
        "investor", "investment", "fundraise", "raise", "seed", "series",
        "valuation", "tam", "sam", "som", "market size", "positioning",
        "gtm", "go-to-market", "competitive advantage", "moat", "strategy",
        "objection", "risk", "due diligence", "pitch", "deck",
        "acquisition", "m&a", "exit", "cap table", "dilution",
    ],
    "technical": [
        "architecture", "code", "api", "infrastructure", "database",
        "microservice", "deployment", "devops", "security", "soc2",
        "product roadmap", "sprint", "technical", "engineering",
        "platform", "integration", "ai agent", "llm", "ml",
        "scalab", "performance", "latency", "uptime",
    ],
    "research": [
        "market", "industry", "trend", "landscape", "competitor",
        "regulation", "policy", "agoa", "trade", "tariff",
        "africa", "kenya", "nigeria", "emerging market",
        "edo", "economic development", "sez", "special economic zone",
        "sector", "analysis", "benchmark", "data",
    ],
    "creative": [
        "content", "blog", "newsletter", "linkedin", "twitter",
        "messaging", "tagline", "headline", "copy", "brand",
        "thought leadership", "article", "narrative", "story",
        "naming", "slogan", "voice", "tone",
    ],
}


def classify_query(query: str) -> str:
    """Auto-classify a query into the best profile based on keyword signals."""
    query_lower = query.lower()
    scores = {}

    for profile, keywords in PROFILE_SIGNALS.items():
        score = sum(1 for kw in keywords if kw in query_lower)
        # Boost for multi-word keyword matches (more specific = more signal)
        score += sum(1 for kw in keywords if len(kw.split()) > 1 and kw in query_lower)
        scores[profile] = score

    best = max(scores, key=scores.get)

    # If no strong signal, default to research (broadest frontier council)
    if scores[best] == 0:
        return DEFAULT_PROFILE

    return best


# ─────────────────────────────────────────────
# Depth Configs
# ─────────────────────────────────────────────

DEPTH_CONFIGS = {
    "quick":    {"max_tokens": 1500,  "temperature": 0.3},
    "standard": {"max_tokens": 4000,  "temperature": 0.4},
    "deep":     {"max_tokens": 8000,  "temperature": 0.5},
}

DEFAULT_RESEARCH_PROMPT = """You are a research analyst providing thorough, evidence-based analysis.

When answering:
1. Lead with your key finding or position — be direct
2. Support with specific evidence, data, or reasoning
3. Note important caveats, risks, or alternative perspectives
4. If uncertain, say so explicitly rather than hedging vaguely
5. Prioritize actionable insight over comprehensive coverage"""

# ─────────────────────────────────────────────
# Core: Model Query Engine
# ─────────────────────────────────────────────

async def query_model(
    model: str,
    query: str,
    system_prompt: str,
    max_tokens: int,
    temperature: float,
    api_key: str,
) -> dict:
    """Query a single model via OpenRouter. Returns structured result."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://harold.council.local",
        "X-Title": "Harold Model Council",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            return {
                "model": model,
                "status": "success",
                "response": content,
                "tokens": {
                    "prompt": usage.get("prompt_tokens", 0),
                    "completion": usage.get("completion_tokens", 0),
                    "total": usage.get("total_tokens", 0),
                },
            }

    except httpx.HTTPStatusError as e:
        error_body = ""
        try:
            error_body = e.response.text[:300]
        except Exception:
            pass
        return {
            "model": model,
            "status": "error",
            "error": f"HTTP {e.response.status_code}: {error_body}",
            "response": None,
        }
    except httpx.TimeoutException:
        return {
            "model": model,
            "status": "error",
            "error": "Request timed out after 180s. Try 'quick' depth or a faster model.",
            "response": None,
        }
    except Exception as e:
        return {
            "model": model,
            "status": "error",
            "error": f"{type(e).__name__}: {str(e)}",
            "response": None,
        }


async def run_council(
    query: str,
    models: Optional[List[str]] = None,
    profile: Optional[str] = None,
    depth: str = "standard",
    system_prompt: Optional[str] = None,
) -> dict:
    """Fan out query to all models concurrently, return structured results."""
    api_key = _get_api_key()
    if not api_key:
        return {"error": "OPENROUTER_API_KEY not set. Set it as an environment variable."}

    # Model selection: explicit models > explicit profile > auto-classify
    if models:
        selected_profile = "custom"
        selected_models = models
    elif profile and profile in PROFILES:
        selected_profile = profile
        selected_models = PROFILES[profile]["models"]
    else:
        selected_profile = classify_query(query)
        selected_models = PROFILES[selected_profile]["models"]

    config = DEPTH_CONFIGS.get(depth, DEPTH_CONFIGS["standard"])
    prompt = system_prompt or DEFAULT_RESEARCH_PROMPT

    # Concurrent fan-out
    tasks = [
        query_model(m, query, prompt, config["max_tokens"], config["temperature"], api_key)
        for m in selected_models
    ]
    results = await asyncio.gather(*tasks)

    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "error"]
    total_tokens = sum(r.get("tokens", {}).get("total", 0) for r in successful)

    return {
        "query": query,
        "profile": selected_profile,
        "profile_description": PROFILES.get(selected_profile, {}).get("description", "Custom model selection"),
        "depth": depth,
        "models_queried": len(selected_models),
        "models_responded": len(successful),
        "models_failed": len(failed),
        "total_tokens": total_tokens,
        "responses": results,
        "chairman_instructions": (
            "SYNTHESIZE these responses as the Chairman. Your job:\n"
            "1. **CONSENSUS** — Where do models agree? High-confidence findings.\n"
            "2. **UNIQUE INSIGHTS** — What did only one model catch? Worth investigating.\n"
            "3. **CONFLICTS** — Where do models disagree? Flag for deeper research.\n"
            "4. **CONFIDENCE** — Rate overall confidence based on convergence.\n"
            "5. **VERDICT** — Your synthesized position, informed by all perspectives + your knowledge base context."
        ),
    }


async def list_available_models() -> dict:
    """Fetch available models from OpenRouter."""
    api_key = _get_api_key()
    if not api_key:
        return {"error": "OPENROUTER_API_KEY not set."}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                OPENROUTER_MODELS_URL,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

            models = []
            for m in data.get("data", []):
                pricing = m.get("pricing", {})
                models.append({
                    "id": m["id"],
                    "name": m.get("name", m["id"]),
                    "context_length": m.get("context_length", 0),
                    "prompt_cost_per_1m": pricing.get("prompt", "?"),
                    "completion_cost_per_1m": pricing.get("completion", "?"),
                })

            models.sort(key=lambda x: x["name"])

            return {
                "total_available": len(models),
                "profiles": {k: v for k, v in PROFILES.items()},
                "models": models,
            }

    except Exception as e:
        return {"error": f"Failed to fetch models: {str(e)}"}


# ─────────────────────────────────────────────
# MCP Server Interface
# ─────────────────────────────────────────────

mcp = FastMCP("model_council_mcp")


class CouncilResearchInput(BaseModel):
    """Input for running a research query across the model council."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="The research question or topic to investigate across multiple models",
        min_length=10,
    )
    profile: Optional[str] = Field(
        default=None,
        description=(
            "Model profile to use. Options: 'strategic' (Opus+o3+Gemini — investment, GTM), "
            "'technical' (Sonnet+GPT-4.1+DeepSeek — product, code), "
            "'research' (Opus+GPT-4.1+Gemini — market analysis), "
            "'creative' (Opus+GPT-4.1+Gemini — content, messaging), "
            "'fast' (Sonnet+GPT-4.1-mini+Flash — quick validation). "
            "If omitted, auto-classifies the query and picks the best profile."
        ),
    )
    models: Optional[List[str]] = Field(
        default=None,
        description=(
            "Override: explicit OpenRouter model IDs. Takes precedence over profile. "
            "Use council_list_models to see available options. Max 5."
        ),
        max_length=5,
    )
    depth: str = Field(
        default="standard",
        description="Research depth: 'quick' (~1.5K tokens/model), 'standard' (~4K), 'deep' (~8K)",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Optional custom system prompt to guide all models. Defaults to research-analyst prompt.",
    )


class CouncilCompareInput(BaseModel):
    """Input for quick side-by-side model comparison."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="Question to compare across models (shorter queries work best)",
        min_length=5,
    )
    profile: Optional[str] = Field(
        default=None,
        description="Model profile. Defaults to 'fast' for quick comparisons.",
    )
    models: Optional[List[str]] = Field(
        default=None,
        description="Override: explicit model IDs. Max 5.",
        max_length=5,
    )


@mcp.tool(
    name="council_research",
    annotations={
        "title": "Model Council — Deep Research",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def council_research(params: CouncilResearchInput) -> str:
    """Run a research query across multiple frontier LLMs simultaneously.

    Sends your query to multiple models via OpenRouter and returns all
    responses for chairman synthesis. Auto-selects the best model profile
    based on query type unless overridden.

    Profiles:
      strategic → Opus 4.5 + o3 + Gemini 2.5 Pro (investment, GTM, positioning)
      technical → Sonnet 4 + GPT-4.1 + DeepSeek R1 (product, architecture)
      research  → Opus 4.5 + GPT-4.1 + Gemini 2.5 Pro (market analysis)
      creative  → Opus 4.5 + GPT-4.1 + Gemini 2.5 Pro (content, messaging)
      fast      → Sonnet 4 + GPT-4.1-mini + Flash (quick validation)

    Harold acts as chairman — synthesizing responses with full knowledge
    base context to produce a final verdict with consensus/conflict mapping.

    Args:
        params: CouncilResearchInput with query, optional profile/models, depth, system prompt.

    Returns:
        JSON string containing all model responses, profile used, plus synthesis instructions.
    """
    result = await run_council(
        query=params.query,
        models=params.models,
        profile=params.profile,
        depth=params.depth,
        system_prompt=params.system_prompt,
    )
    return json.dumps(result, indent=2)


@mcp.tool(
    name="council_compare",
    annotations={
        "title": "Model Council — Quick Compare",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def council_compare(params: CouncilCompareInput) -> str:
    """Quick side-by-side comparison for simpler questions.

    Lighter than council_research — shorter responses, good for
    fact-checking, opinion comparison, or quick validation.
    Uses the 'fast' profile by default.

    Args:
        params: CouncilCompareInput with query and optional profile/models.

    Returns:
        JSON string with all model responses side by side.
    """
    result = await run_council(
        query=params.query,
        models=params.models,
        profile=params.profile or "fast",
        depth="quick",
    )
    result.pop("chairman_instructions", None)
    return json.dumps(result, indent=2)


@mcp.tool(
    name="council_list_models",
    annotations={
        "title": "List Available Models & Profiles",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def council_list_models() -> str:
    """List available profiles and all models on OpenRouter with pricing.

    Shows the 5 built-in profiles and their model assignments,
    plus the full OpenRouter catalog for custom configurations.
    """
    result = await list_available_models()
    return json.dumps(result, indent=2)


# ─────────────────────────────────────────────
# CLI Interface (for direct testing)
# ─────────────────────────────────────────────

def cli():
    """Run council from command line for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Model Council — Multi-LLM Research")
    parser.add_argument("query", nargs="?", help="Research query")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode (not MCP)")
    parser.add_argument("--depth", default="standard", choices=["quick", "standard", "deep"])
    parser.add_argument("--profile", default=None, choices=list(PROFILES.keys()),
                        help="Model profile (default: auto-classify)")
    parser.add_argument("--models", default=None, help="Comma-separated model IDs (overrides profile)")
    parser.add_argument("--list-models", action="store_true", help="List available models")
    parser.add_argument("--list-profiles", action="store_true", help="List profiles")
    parser.add_argument("--compare", action="store_true", help="Quick compare mode")

    args = parser.parse_args()

    if not args.cli and not args.list_models and not args.list_profiles:
        mcp.run()
        return

    if args.list_profiles:
        for name, info in PROFILES.items():
            models_str = ", ".join(m.split("/")[1] for m in info["models"])
            print(f"  {name:12s}  {info['description']}")
            print(f"  {'':12s}  → {models_str}")
            print()
        return

    if args.list_models:
        result = asyncio.run(list_available_models())
        print(json.dumps(result, indent=2))
        return

    if not args.query:
        parser.error("Query is required in CLI mode")
        return

    models = args.models.split(",") if args.models else None

    result = asyncio.run(run_council(
        query=args.query,
        models=models,
        profile="fast" if args.compare else args.profile,
        depth="quick" if args.compare else args.depth,
    ))

    if args.compare:
        result.pop("chairman_instructions", None)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    if any(flag in sys.argv for flag in ["--cli", "--list-models", "--list-profiles"]):
        cli()
    else:
        mcp.run()
