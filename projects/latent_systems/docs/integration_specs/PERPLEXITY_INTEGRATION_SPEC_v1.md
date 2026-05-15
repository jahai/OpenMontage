# Perplexity Integration Spec for the Latent Systems Production App

## Overview

The Latent Systems app should integrate Perplexity as the truth, research, citation, and factual QA layer for episode production. Perplexity should not replace Claude, ComfyUI, Higgsfield, or the editor. Its job is to make every script beat, shot card, prompt, and approved asset traceable to sources, while helping the app identify unsupported claims, visual anachronisms, and misleading causal implications before generation or final edit.

The recommended MVP uses two Perplexity API primitives: the Search API for raw ranked web results and Sonar for web-grounded answers with source tracking. Perplexity’s quickstart describes Search as the right API when an app needs raw search data without LLM processing, and Sonar as the right API when an app needs researched Q&A with citations and conversation context ([Perplexity Quickstart](https://docs.perplexity.ai/docs/getting-started/quickstart)). Perplexity’s Search endpoint returns ranked pages with title, URL, snippet, date, and last-updated fields, which makes it suitable for creating source candidates before asking an LLM to synthesize anything ([Perplexity Search API](https://docs.perplexity.ai/api-reference/search-post)). The Sonar model is optimized for fast, grounded answers, supports a 128K context length, and returns search metadata including source titles, URLs, dates, snippets, and citation URLs ([Sonar model docs](https://docs.perplexity.ai/docs/sonar/models/sonar)).

## Product Role

### What Perplexity Should Do

- **Research cards**: Generate sourced research cards for every factual claim, historical scene, visual motif, quote, date, institution, prop, and psychological concept.
- **Claim checking**: Compare narration, lower-thirds, on-screen text, and episode notes against available sources.
- **Visual constraints**: Produce historically grounded “must include,” “safe inference,” and “avoid” constraints before ComfyUI or Higgsfield generation.
- **Prompt grounding**: Convert research cards into prompt constraints that reduce visual hallucination.
- **Citation tracking**: Preserve source URLs and source metadata on every generated research card and claim check.
- **Editorial QA**: Flag when a scene implies causation that the research does not support.

### What Perplexity Should Not Do

- **No primary generation role**: Perplexity should not generate the final image/video assets.
- **No final editorial authority**: Perplexity can flag risks, but the app should leave final approval to the user.
- **No unsourced invented detail**: The app should treat uncited Perplexity output as draft reasoning, not production truth.
- **No replacement for ComfyUI metadata**: Perplexity should not store seed, LoRA, model, workflow JSON, or render metadata unless attached as review context.
- **No automated publishing**: The integration should not publish, upload, or post content without explicit user action.

## Architecture

```txt
Latent Systems App
  Script Beats
  Research Cards
  Shot Cards
  Reference Packs
  Generation Jobs
  Assets
  Review Notes
      |
      | server-side calls
      v
Perplexity Research Service
  Search API
  Sonar API
  Claim Checker
  Visual Constraint Builder
  Citation Normalizer
      |
      v
Claude Orchestration Layer
  App feature implementation
  Shot-to-workflow conversion
  ComfyUI workflow submission
  Higgsfield prompt/routing
      |
      v
ComfyUI / Higgsfield / Editor
```

### Service Boundary

The app should call Perplexity only from the backend. The frontend should never expose the Perplexity API key. The backend service should expose application-specific endpoints such as `/api/research/cards`, `/api/qa/claim-check`, and `/api/prompts/visual-constraints`, rather than exposing raw Perplexity endpoints directly to the browser.

### API Selection Rules

| App need | Use | Reason |
| --- | --- | --- |
| Find candidate sources for a topic | Search API | The Search API returns raw ranked web results without LLM synthesis, which is useful for source discovery and custom workflows ([Perplexity Quickstart](https://docs.perplexity.ai/docs/getting-started/quickstart)). |
| Generate a sourced answer or research card | Sonar | Sonar is designed for grounded Q&A and returns source metadata and citations with the answer ([Sonar model docs](https://docs.perplexity.ai/docs/sonar/models/sonar)). |
| Build custom source curation UI | Search API + app ranking | Search results include title, URL, snippet, date, and last-updated fields that can be stored, filtered, and shown to the user ([Perplexity Search API](https://docs.perplexity.ai/api-reference/search-post)). |
| Check one narration line against sources | Sonar | The app needs synthesis and evidence evaluation, not just links. |
| Create historically grounded prompt constraints | Sonar | The app needs a structured output that turns research into production constraints. |
| Populate long-term semantic memory | Embeddings later | Perplexity’s quickstart lists Embeddings as the API area for semantic search and RAG, but this should be a later phase after the core production workflow is stable ([Perplexity Quickstart](https://docs.perplexity.ai/docs/getting-started/quickstart)). |

## MVP User Stories

### P0 Stories

- **Research card creation**: As the creator, I want to generate a sourced research card from a topic or script beat so that every visual and narration decision has traceable evidence.
- **Claim check**: As the creator, I want to check a narration sentence against sources so that I do not accidentally overstate causality or invent a historical claim.
- **Visual constraint generation**: As the creator, I want the app to turn research into prompt constraints so that ComfyUI and Higgsfield prompts stay historically grounded.
- **Source attachment**: As the creator, I want source URLs stored with each card and claim check so that citations survive across rewrites, prompts, and edits.
- **Risk labeling**: As the creator, I want each claim labeled as verified, likely, inferred, creative metaphor, unsupported, or contradicted so that I know which lines are safe.

### P1 Stories

- **Asset QA**: As the creator, I want to upload or select a generated image/video still and have the app check it against the research card so that I can catch visual anachronisms.
- **Source candidate review**: As the creator, I want to see the raw source candidates before synthesis so that I can exclude low-quality or irrelevant sources.
- **Prompt revision**: As the creator, I want the app to rewrite a prompt after QA flags so that I can regenerate corrected assets quickly.
- **Research refresh**: As the creator, I want to refresh an old research card so that newer or better sources can be incorporated.

### P2 Stories

- **Batch research**: As the creator, I want to generate research cards for every script beat in one batch so that a full episode can be prepared faster.
- **Citation export**: As the creator, I want to export all cited sources for an episode so that show notes and production documentation are easier.
- **Semantic source library**: As the creator, I want semantic search over prior research cards so that later episodes can reuse verified context.

## Data Model Additions

### ResearchSource

```ts
type ResearchSource = {
  id: string;
  title: string;
  url: string;
  domain: string;
  snippet?: string;
  date?: string;
  lastUpdated?: string;
  sourceType?: "primary" | "secondary" | "academic" | "archive" | "news" | "unknown";
  credibilityNote?: string;
  fetchedAt: string;
};
```

### ResearchCard

```ts
type ResearchCard = {
  id: string;
  projectId: string;
  episodeId: string;
  scriptBeatId?: string;
  topic: string;
  question: string;
  answer: string;
  keyFacts: string[];
  visualImplications: string[];
  safeInferences: string[];
  avoidClaims: string[];
  sources: ResearchSource[];
  confidence: "high" | "medium" | "low";
  status: "draft" | "reviewed" | "approved" | "deprecated";
  createdAt: string;
  updatedAt: string;
};
```

### ClaimCheck

```ts
type ClaimCheck = {
  id: string;
  claimText: string;
  verdict: "verified" | "likely" | "inferred" | "creative_metaphor" | "unsupported" | "contradicted";
  explanation: string;
  requiredRevision?: string;
  sources: ResearchSource[];
  riskTags: Array<
    "causality_overreach" |
    "anachronism" |
    "quote_risk" |
    "visual_implication_risk" |
    "unsupported_specificity" |
    "source_conflict"
  >;
  createdAt: string;
};
```

### VisualConstraintSet

```ts
type VisualConstraintSet = {
  id: string;
  shotCardId: string;
  researchCardIds: string[];
  mustInclude: string[];
  mayInclude: string[];
  avoid: string[];
  anachronismRisks: string[];
  promptAddendum: string;
  negativePromptAddendum: string;
  sourceIds: string[];
  createdAt: string;
};
```

## Backend Endpoints

### Create Research Card

```http
POST /api/research/cards
```

Request:

```json
{
  "episodeId": "ep1",
  "scriptBeatId": "beat_skinner_003",
  "topic": "B.F. Skinner Harvard apparatus 1930s",
  "question": "What should the apparatus and lab environment look like for a historically grounded 1930s Harvard Skinner sequence?",
  "mode": "historical_visual_research",
  "preferredDomains": ["bfskinner.org", "harvard.edu", "gettyimages.com"]
}
```

Response:

```json
{
  "researchCard": {
    "id": "rc_123",
    "topic": "B.F. Skinner Harvard apparatus 1930s",
    "answer": "...",
    "keyFacts": [],
    "visualImplications": [],
    "safeInferences": [],
    "avoidClaims": [],
    "sources": [],
    "confidence": "medium",
    "status": "draft"
  }
}
```

Acceptance criteria:

- Given a script beat with a topic, when the user clicks “Generate research card,” then the backend creates a ResearchCard with at least three candidate sources when available.
- Given Perplexity returns sources, when the card is saved, then each source URL is persisted in ResearchSource.
- Given sources conflict, when the card is generated, then the confidence is not “high” and the answer includes a source conflict note.

### Claim Check

```http
POST /api/qa/claim-check
```

Request:

```json
{
  "episodeId": "ep1",
  "claimText": "This is where infinite scroll began.",
  "context": "Narration line in Skinner sequence",
  "relatedResearchCardIds": ["rc_123"]
}
```

Response:

```json
{
  "claimCheck": {
    "id": "cc_123",
    "verdict": "contradicted",
    "explanation": "The line implies direct causation between Skinner's experiments and infinite scroll. The safer formulation is that the research made a behavioral pattern visible.",
    "requiredRevision": "This is not where infinite scroll began. But it is where a pattern became visible.",
    "sources": [],
    "riskTags": ["causality_overreach"]
  }
}
```

Acceptance criteria:

- Given a claim that overstates causality, when the user runs claim check, then the result includes a risk tag of `causality_overreach`.
- Given a claim is unsupported, when the user runs claim check, then the verdict is not `verified`.
- Given the claim can be made safer, when the result is returned, then `requiredRevision` contains a production-ready rewrite.

### Generate Visual Constraints

```http
POST /api/prompts/visual-constraints
```

Request:

```json
{
  "shotCardId": "shot_skinner_apparatus_macro",
  "researchCardIds": ["rc_123", "rc_124"],
  "generationTarget": "comfyui",
  "stylePackId": "style_ep1_latent_systems"
}
```

Response:

```json
{
  "constraints": {
    "mustInclude": [
      "hand-built electromechanical apparatus",
      "lever",
      "food magazine",
      "wood, brass, wire, relay details"
    ],
    "mayInclude": [
      "paper recording mechanism",
      "period institutional lab table"
    ],
    "avoid": [
      "modern LED displays",
      "plastic enclosures",
      "Esterline-Angus paper-tape recorder",
      "modern fluorescent laboratory"
    ],
    "promptAddendum": "...",
    "negativePromptAddendum": "..."
  }
}
```

Acceptance criteria:

- Given approved research cards, when visual constraints are generated, then the constraints include separate `mustInclude`, `mayInclude`, and `avoid` arrays.
- Given a target of `comfyui`, when constraints are generated, then the response includes concise prompt and negative-prompt addenda.
- Given a target of `higgsfield`, when constraints are generated, then the response emphasizes motion, camera, duration, and reference-image use.

## Perplexity Service Implementation

### Environment

```env
PERPLEXITY_API_KEY=...
PERPLEXITY_BASE_URL=https://api.perplexity.ai
```

### Search API Wrapper

Use the Search API for source discovery. The documented endpoint is `POST https://api.perplexity.ai/search`, with bearer authorization and a JSON request body including the required `query` field ([Perplexity Search API](https://docs.perplexity.ai/api-reference/search-post)). Optional filters include domain filtering, language filtering, recency filters, date filters, country, and max result controls ([Perplexity Search API](https://docs.perplexity.ai/api-reference/search-post)).

```ts
async function searchSources(input: {
  query: string;
  domains?: string[];
  maxResults?: number;
}) {
  const res = await fetch("https://api.perplexity.ai/search", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${process.env.PERPLEXITY_API_KEY}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      query: input.query,
      max_results: input.maxResults ?? 10,
      search_domain_filter: input.domains
    })
  });

  if (!res.ok) throw new Error(`Perplexity Search failed: ${res.status}`);
  return res.json();
}
```

### Sonar Wrapper

Use Sonar for grounded synthesis. The documented Sonar endpoint is `https://api.perplexity.ai/v1/sonar`, and the `sonar` model is described as a fast, cost-efficient search model for grounded answers with real-time web search ([Sonar model docs](https://docs.perplexity.ai/docs/sonar/models/sonar)). Sonar responses include generated content, usage details, citations, and `search_results` metadata such as title, URL, date, last-updated date, and snippet ([Sonar model docs](https://docs.perplexity.ai/docs/sonar/models/sonar)).

```ts
async function askSonar(input: {
  system: string;
  user: string;
  model?: "sonar" | "sonar-pro";
}) {
  const res = await fetch("https://api.perplexity.ai/v1/sonar", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${process.env.PERPLEXITY_API_KEY}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model: input.model ?? "sonar",
      messages: [
        { role: "system", content: input.system },
        { role: "user", content: input.user }
      ]
    })
  });

  if (!res.ok) throw new Error(`Perplexity Sonar failed: ${res.status}`);
  return res.json();
}
```

## Prompt Contracts

### Research Card System Prompt

```txt
You are the research layer for a documentary production app. Return only JSON.
Ground every factual statement in sources. Separate verified facts from safe inference.
Do not invent quotes, dates, images, or causal relationships.
If sources conflict or are weak, lower confidence and explain why.
For visual production, include must-include details, safe visual inferences, and avoid claims.
```

### Research Card User Prompt

```txt
Episode: {episodeTitle}
Script beat: {scriptBeatText}
Research question: {question}
Preferred source types: primary sources, archives, academic sources, official institutions
Visual target: {shotType}

Return:
{
  "answer": string,
  "keyFacts": string[],
  "visualImplications": string[],
  "safeInferences": string[],
  "avoidClaims": string[],
  "confidence": "high" | "medium" | "low",
  "sourceQualityNotes": string[]
}
```

### Claim Check System Prompt

```txt
You are a documentary claim checker. Return only JSON.
Evaluate whether the claim is verified, likely, inferred, creative metaphor, unsupported, or contradicted.
Flag causality overreach, anachronism, invented quote risk, unsupported specificity, and visual implication risk.
If the claim is unsafe, provide a safer rewrite that preserves drama without overstating evidence.
```

### Visual Constraint System Prompt

```txt
You convert approved research cards into image/video generation constraints.
Return only JSON. Do not add unsourced specificity.
Separate mustInclude, mayInclude, avoid, anachronismRisks, promptAddendum, and negativePromptAddendum.
Optimize for generation reliability without sacrificing factual accuracy.
```

## Episode 1 Skinner-Specific Integration

### Required App Behavior

- Every Skinner shot card should require a linked ResearchCard before the shot can move to “Prompt drafted.”
- Every prompt sent to ComfyUI or Higgsfield should include a VisualConstraintSet generated from approved research.
- Any narration line that directly connects Skinner to apps, social media, or infinite scroll should require a claim check.
- The app should treat “behavioral continuity” as safe framing and “Skinner invented infinite scroll” as a blocked framing.
- Any generated asset showing old Skinner, lab coat Skinner, modern lab props, modern electronics, or unsupported lab architecture should be flagged for review.

### Default Skinner Claim Policy

| Claim type | App default |
| --- | --- |
| “Skinner studied reinforcement patterns in controlled experiments.” | Allowed if sourced. |
| “Skinner invented infinite scroll.” | Blocked. |
| “Skinner caused smartphone addiction.” | Blocked. |
| “The same behavioral pattern appears in modern app design.” | Allowed as analytical framing if phrased carefully. |
| “This is not where infinite scroll began. But it is where a pattern became visible.” | Preferred framing. |

## UI Requirements

### Research Drawer

Each ScriptBeat and ShotCard should have a Research Drawer with:

- Linked research cards.
- Claim checks.
- Source list.
- Confidence labels.
- Visual constraints.
- “Regenerate research” button.
- “Create prompt constraints” button.

### Claim Risk Badge

Display claim status as a badge:

- Green: verified.
- Blue: likely.
- Purple: creative metaphor.
- Yellow: inferred.
- Orange: unsupported.
- Red: contradicted.

### Generation Gate

A shot cannot be marked “Ready for generation” unless:

- At least one ResearchCard is linked.
- VisualConstraintSet exists.
- Any high-risk claims are reviewed.
- Required references are attached.

## Success Metrics

### MVP Metrics

- 90% of final episode visual shots have linked research cards.
- 100% of factual narration beats have at least one claim check.
- 0 known unsupported direct-causation claims survive into the final Skinner sequence.
- Median time from script beat to sourced shot card is under 10 minutes after workflow stabilization.
- At least 75% of rejected generations include a structured rejection reason that can improve the next prompt.

### Quality Metrics

- Fewer visual anachronisms per review pass.
- Fewer prompt rewrites caused by missing historical constraints.
- Higher reuse of approved reference packs.
- Lower number of “looks cool but is wrong” assets.

## Implementation Plan

### Phase 1: Thin Perplexity Service

- Add backend environment variable for `PERPLEXITY_API_KEY`.
- Create `perplexityService.ts`.
- Implement `searchSources`.
- Implement `askSonar`.
- Normalize returned source metadata into `ResearchSource`.
- Log raw provider response IDs for debugging.

### Phase 2: Research Cards

- Add ResearchCard and ResearchSource database tables.
- Build `/api/research/cards`.
- Add Research Drawer UI.
- Allow source review and manual approval.

### Phase 3: Claim Check

- Add ClaimCheck table.
- Build `/api/qa/claim-check`.
- Add risk badges to ScriptBeat and ShotCard.
- Block high-risk claims from “approved” status until reviewed.

### Phase 4: Visual Constraints

- Add VisualConstraintSet table.
- Build `/api/prompts/visual-constraints`.
- Append constraints to ComfyUI and Higgsfield prompt builders.
- Store promptAddendum and negativePromptAddendum with each PromptVersion.

### Phase 5: Asset QA

- Add generated asset review flow.
- Compare selected asset against linked ResearchCard and VisualConstraintSet.
- Store ReviewNote outputs.
- Add “revise prompt from QA flags” action.

## Open Questions

- **API model choice**: Should MVP default to `sonar` for speed and use `sonar-pro` only for higher-stakes synthesis?
- **Source policy**: Which domains should be trusted by default for episode 1 historical research?
- **Manual approval**: Should all research cards require manual approval before prompts can use them?
- **Vision QA**: Should visual QA use Perplexity only for research context, or should the app pair Perplexity research with a separate vision model for image analysis?
- **Local storage**: Should raw Perplexity responses be stored for auditability, or only normalized cards and source metadata?

## Claude Code Build Brief

Build a Perplexity-backed research module inside the Latent Systems production app. Implement backend-only Perplexity calls, starting with source discovery, research card generation, claim checking, and visual constraint generation. Store normalized source metadata, attach cards to script beats and shot cards, and use the outputs to gate ComfyUI/Higgsfield generation readiness. Do not expose the Perplexity API key to the frontend. Do not implement final image generation inside this module. The module’s first purpose is to make episode 1 visually precise, historically grounded, and less prone to unsupported Skinner-to-smartphone causality claims.
