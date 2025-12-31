# Contract: Turn Report Schema

**Date**: December 31, 2025  
**Feature**: 002-navigator-agent

---

## Overview

The Turn Report is the structured output presented to users in interactive mode after each exploration iteration. It provides visibility into the agent's progress and enables informed decisions about continuing exploration.

## Data Structure

### TurnReport

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TurnReport:
    """Report returned after each interactive turn."""
    
    # Iteration info
    step_number: int
    timestamp: datetime
    
    # Cost tracking
    cost_this_turn: float  # USD
    total_cost: float      # USD
    budget_remaining: float  # USD
    budget_percentage: float  # 0-100
    
    # Map metrics
    map_size_tokens: int
    token_budget: int
    token_utilization: float  # 0-100
    file_count: int
    
    # Focus summary
    focus_areas: list[FocusArea]
    excluded_areas: list[str]
    
    # Agent reasoning
    last_action: str
    reasoning: str
    
    # Status
    is_complete: bool
    completion_reason: str | None  # "agent_done", "budget_exceeded", etc.


@dataclass
class FocusArea:
    """A path currently at high verbosity."""
    path: str
    verbosity_level: int
    token_contribution: int
```

## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TurnReport",
  "type": "object",
  "required": [
    "step_number",
    "timestamp",
    "cost_this_turn",
    "total_cost",
    "budget_remaining",
    "map_size_tokens",
    "token_budget",
    "file_count",
    "focus_areas",
    "last_action",
    "reasoning",
    "is_complete"
  ],
  "properties": {
    "step_number": {
      "type": "integer",
      "minimum": 1,
      "description": "Current iteration number"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "When this turn completed"
    },
    "cost_this_turn": {
      "type": "number",
      "minimum": 0,
      "description": "USD cost of the last iteration"
    },
    "total_cost": {
      "type": "number",
      "minimum": 0,
      "description": "Cumulative USD cost"
    },
    "budget_remaining": {
      "type": "number",
      "minimum": 0,
      "description": "Remaining USD budget"
    },
    "budget_percentage": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "description": "Percentage of cost budget used"
    },
    "map_size_tokens": {
      "type": "integer",
      "minimum": 0,
      "description": "Current map token count"
    },
    "token_budget": {
      "type": "integer",
      "minimum": 0,
      "description": "Target token budget"
    },
    "token_utilization": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "description": "Percentage of token budget used"
    },
    "file_count": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of files in current map"
    },
    "focus_areas": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/FocusArea"
      },
      "description": "Paths at high verbosity (L3-L4)"
    },
    "excluded_areas": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Paths at L0 (excluded)"
    },
    "last_action": {
      "type": "string",
      "description": "What the agent did in this turn"
    },
    "reasoning": {
      "type": "string",
      "description": "Agent's explanation for the action"
    },
    "is_complete": {
      "type": "boolean",
      "description": "Whether exploration is finished"
    },
    "completion_reason": {
      "type": "string",
      "nullable": true,
      "enum": ["agent_done", "budget_exceeded", "max_iterations", "user_cancelled", null],
      "description": "Why exploration completed (if is_complete)"
    }
  },
  "definitions": {
    "FocusArea": {
      "type": "object",
      "required": ["path", "verbosity_level"],
      "properties": {
        "path": {
          "type": "string",
          "description": "File or directory path"
        },
        "verbosity_level": {
          "type": "integer",
          "minimum": 3,
          "maximum": 4,
          "description": "Current verbosity level"
        },
        "token_contribution": {
          "type": "integer",
          "minimum": 0,
          "description": "Tokens contributed by this path"
        }
      }
    }
  }
}
```

## Example Turn Report

```json
{
  "step_number": 3,
  "timestamp": "2025-12-31T10:35:00Z",
  "cost_this_turn": 0.0012,
  "total_cost": 0.0036,
  "budget_remaining": 1.9964,
  "budget_percentage": 0.18,
  "map_size_tokens": 15200,
  "token_budget": 20000,
  "token_utilization": 76.0,
  "file_count": 47,
  "focus_areas": [
    {
      "path": "src/auth/",
      "verbosity_level": 4,
      "token_contribution": 8500
    },
    {
      "path": "src/middleware/auth.py",
      "verbosity_level": 4,
      "token_contribution": 1200
    },
    {
      "path": "src/models/user.py",
      "verbosity_level": 3,
      "token_contribution": 800
    }
  ],
  "excluded_areas": [
    "node_modules/",
    ".git/",
    "docs/api/"
  ],
  "last_action": "Increased verbosity on src/models/user.py to L3",
  "reasoning": "The User model is referenced by the auth middleware. Including its interface (signatures and docstrings) provides context for how user data flows through authentication without including full implementation details.",
  "is_complete": false,
  "completion_reason": null
}
```

## CLI Rendering

### Compact Format (Default)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ TURN REPORT - Step 3                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ Cost:  $0.0012 this turn | $0.0036 total (0.2% of $2.00)               │
│ Size:  15,200 tokens (76% of 20,000) | 47 files                        │
│                                                                         │
│ Focus: src/auth/ (L4), src/middleware/auth.py (L4), src/models/user.py │
│                                                                         │
│ Action: Increased verbosity on src/models/user.py to L3                │
│ Reason: User model referenced by auth - including interface for context│
└─────────────────────────────────────────────────────────────────────────┘

Continue? [y/N/feedback]: 
```

### Verbose Format (--verbose flag)

```
╔═════════════════════════════════════════════════════════════════════════╗
║ TURN REPORT - Step 3                                    2025-12-31 10:35║
╠═════════════════════════════════════════════════════════════════════════╣
║ COST TRACKING                                                           ║
║ ─────────────────────────────────────────────────────────────────────── ║
║ This turn:     $0.0012                                                  ║
║ Total spent:   $0.0036                                                  ║
║ Remaining:     $1.9964                                                  ║
║ Budget used:   ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0.2%║
║                                                                         ║
║ TOKEN UTILIZATION                                                       ║
║ ─────────────────────────────────────────────────────────────────────── ║
║ Current:       15,200 tokens                                            ║
║ Budget:        20,000 tokens                                            ║
║ Utilization:   ████████████████████████████████████████░░░░░░░░░░░  76%║
║ Files:         47 included                                              ║
║                                                                         ║
║ FOCUS AREAS (High Verbosity)                                            ║
║ ─────────────────────────────────────────────────────────────────────── ║
║ • src/auth/                    L4 (full)     ~8,500 tokens              ║
║ • src/middleware/auth.py       L4 (full)     ~1,200 tokens              ║
║ • src/models/user.py           L3 (interface)  ~800 tokens              ║
║                                                                         ║
║ EXCLUDED AREAS                                                          ║
║ ─────────────────────────────────────────────────────────────────────── ║
║ node_modules/, .git/, docs/api/                                         ║
║                                                                         ║
║ AGENT REASONING                                                         ║
║ ─────────────────────────────────────────────────────────────────────── ║
║ Action: Increased verbosity on src/models/user.py to L3                 ║
║                                                                         ║
║ The User model is referenced by the auth middleware. Including its      ║
║ interface (signatures and docstrings) provides context for how user     ║
║ data flows through authentication without including full implementation ║
║ details.                                                                 ║
╚═════════════════════════════════════════════════════════════════════════╝

Continue exploration? [y/N/feedback]: 
```

## User Interaction Options

| Input | Action |
|-------|--------|
| `y` or `yes` | Continue to next iteration |
| `n`, `no`, or Enter | Stop exploration, output current context |
| `feedback: <text>` | Continue with user feedback injected into next prompt |
| `show` | Display current map content |
| `plan` | Display current flight plan YAML |
| `cost` | Show detailed cost breakdown |
| `q` or `quit` | Cancel exploration without output |

## Building TurnReport

```python
from repo_map.navigator.state import NavigatorState, get_navigator_state

def build_turn_report(context: ReadonlyContext) -> TurnReport:
    """Build TurnReport from current navigator state."""
    state = get_navigator_state(context)
    
    # Get last decision
    last_entry = state.decision_log[-1] if state.decision_log else None
    
    return TurnReport(
        step_number=len(state.decision_log),
        timestamp=datetime.now(),
        cost_this_turn=last_entry.cost if last_entry else 0.0,
        total_cost=state.budget_config.current_spend_usd,
        budget_remaining=state.budget_config.max_spend_usd - state.budget_config.current_spend_usd,
        budget_percentage=(state.budget_config.current_spend_usd / state.budget_config.max_spend_usd) * 100,
        map_size_tokens=state.map_metadata.total_tokens,
        token_budget=state.flight_plan.budget,
        token_utilization=(state.map_metadata.total_tokens / state.flight_plan.budget) * 100,
        file_count=state.map_metadata.file_count,
        focus_areas=[
            FocusArea(path=p, verbosity_level=4, token_contribution=0)
            for p in state.map_metadata.focus_areas
        ],
        excluded_areas=[],  # Could track separately
        last_action=last_entry.action if last_entry else "Initial scan",
        reasoning=last_entry.reasoning if last_entry else "",
        is_complete=state.exploration_complete,
        completion_reason=None,
    )
```
