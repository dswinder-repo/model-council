# Model Council

**Multi-LLM research tool for Harold.** Inspired by [Perplexity Model Council](https://www.perplexity.ai/hub/blog/introducing-model-council) and Altimeter's Axiom Council.

Sends research queries to multiple frontier models simultaneously via [OpenRouter](https://openrouter.ai), then Harold acts as "Chairman" — synthesizing all responses with full knowledge base context.

---

## Architecture

```
Query → OpenRouter → [Claude Sonnet 4, GPT-4.1, Gemini 2.5 Pro]
                              ↓ (concurrent)
                      Structured JSON responses
                              ↓
                    Harold (Chairman) synthesizes:
                    - Consensus (high confidence)
                    - Unique insights (investigate)
                    - Conflicts (dig deeper)
                    - Final verdict (with KB context)
```

## Tools (MCP)

| Tool | Description |
|------|-------------|
| `council_research` | Deep research across 3+ models. Returns structured responses for chairman synthesis. |
| `council_compare` | Quick side-by-side comparison for simpler questions. |
| `council_list_models` | List all models available on OpenRouter with pricing. |

## Depth Settings

| Depth | Tokens/Model | Best For |
|-------|-------------|----------|
| `quick` | ~1,500 | Fact-checking, quick validation |
| `standard` | ~4,000 | General research, strategic questions |
| `deep` | ~8,000 | Investment research, competitive analysis |

## Setup

### Prerequisites
- Python 3.10+
- OpenRouter API key ([get one here](https://openrouter.ai/settings/keys))

### Install
```bash
cd /path/to/Claude/labs/model-council
bash setup.sh
```

### Configure in Cowork

**Option 1 — Claude Desktop app:**
1. Open Claude Desktop → Settings → Developer → MCP Servers
2. Add a new server:
   - Name: `model-council`
   - Command: `python3`
   - Args: `/path/to/Claude/labs/model-council/server.py`
   - Env: `OPENROUTER_API_KEY=sk-or-v1-...`

**Option 2 — Claude Code CLI:**
```bash
claude mcp add model-council -- python3 /path/to/Claude/labs/model-council/server.py
```

**Option 3 — Quick CLI test (no Cowork integration):**
```bash
OPENROUTER_API_KEY=sk-or-v1-... python3 server.py --cli "What are the biggest risks for tech companies entering African markets?"
```

### Usage in Harold Sessions

Once configured as an MCP server, Harold can invoke the council mid-conversation:

> "Council this: What's the strongest objection an investor would raise about our TAM calculation?"

Harold will:
1. Call `council_research` with the query
2. Receive responses from all 3 models
3. Synthesize as Chairman with full knowledge base context
4. Present consensus, unique insights, conflicts, and final verdict

### Custom Model Selection

Override the default council with any OpenRouter-supported model:

```bash
python3 server.py --cli --models "openai/o3,anthropic/claude-opus-4-5,deepseek/deepseek-r1" "Your query"
```

## Cost

Approximate per-query costs (3 models, standard depth):
- Quick: ~$0.02-0.05
- Standard: ~$0.05-0.15
- Deep: ~$0.10-0.30

OpenRouter charges per-token with no subscription. Load credits as needed.

---

*Part of Harold Labs. See `labs/README.md` for isolation rules.*
