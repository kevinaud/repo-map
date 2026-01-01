# Contract: Navigator State Schema

**Date**: December 31, 2025  
**Feature**: 002-navigator-agent

---

## Overview

This document defines the schema for `NavigatorState`, the root Pydantic model that holds all state for the Navigator agent. The state is serialized to `session.state["navigator"]` in ADK.

## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "NavigatorState",
  "type": "object",
  "required": ["user_task", "repo_path", "budget_config", "flight_plan"],
  "properties": {
    "user_task": {
      "type": "string",
      "minLength": 1,
      "description": "The user's goal/task description"
    },
    "repo_path": {
      "type": "string",
      "description": "Absolute path to repository being explored"
    },
    "execution_mode": {
      "type": "string",
      "enum": ["autonomous", "interactive"],
      "default": "autonomous",
      "description": "Execution mode for the navigator"
    },
    "budget_config": {
      "$ref": "#/definitions/BudgetConfig"
    },
    "flight_plan": {
      "$ref": "#/definitions/FlightPlan"
    },
    "decision_log": {
      "type": "array",
      "items": { "$ref": "#/definitions/DecisionLogEntry" },
      "default": [],
      "description": "History of decisions made during exploration"
    },
    "map_metadata": {
      "$ref": "#/definitions/MapMetadata"
    },
    "interactive_pause": {
      "type": "boolean",
      "default": false,
      "description": "Flag set when interactive mode should pause"
    },
    "exploration_complete": {
      "type": "boolean",
      "default": false,
      "description": "Flag set when exploration is finished"
    },
    "reasoning_summary": {
      "type": "string",
      "default": "",
      "description": "Final reasoning summary from finalize_context"
    }
  },
  "definitions": {
    "BudgetConfig": {
      "type": "object",
      "required": ["model_pricing_rates"],
      "properties": {
        "max_spend_usd": {
          "type": "number",
          "exclusiveMinimum": 0,
          "default": 2.0,
          "description": "Maximum allowed spend in USD"
        },
        "current_spend_usd": {
          "type": "number",
          "minimum": 0,
          "default": 0.0,
          "description": "Amount spent so far in USD"
        },
        "model_pricing_rates": {
          "$ref": "#/definitions/ModelPricingRates"
        }
      }
    },
    "ModelPricingRates": {
      "type": "object",
      "required": ["model_name", "input_per_million", "output_per_million"],
      "properties": {
        "model_name": {
          "type": "string",
          "description": "Model identifier"
        },
        "input_per_million": {
          "type": "number",
          "exclusiveMinimum": 0,
          "description": "USD per 1M input tokens"
        },
        "output_per_million": {
          "type": "number",
          "exclusiveMinimum": 0,
          "description": "USD per 1M output tokens"
        }
      }
    },
    "DecisionLogEntry": {
      "type": "object",
      "required": ["step", "action", "reasoning"],
      "properties": {
        "step": {
          "type": "integer",
          "minimum": 1,
          "description": "Step number (1-indexed)"
        },
        "action": {
          "type": "string",
          "enum": ["update_flight_plan", "finalize_context"],
          "description": "Action type"
        },
        "reasoning": {
          "type": "string",
          "minLength": 1,
          "description": "Explanation for the decision"
        },
        "config_diff": {
          "type": "object",
          "description": "Partial FlightPlan changes applied"
        },
        "timestamp": {
          "type": "string",
          "format": "date-time",
          "description": "When the decision was made"
        }
      }
    },
    "MapMetadata": {
      "type": "object",
      "properties": {
        "total_tokens": {
          "type": "integer",
          "minimum": 0,
          "default": 0,
          "description": "Estimated token count of current map"
        },
        "file_count": {
          "type": "integer",
          "minimum": 0,
          "default": 0,
          "description": "Number of files in map"
        },
        "focus_areas": {
          "type": "array",
          "items": { "type": "string" },
          "default": [],
          "description": "Paths at high verbosity"
        },
        "excluded_count": {
          "type": "integer",
          "minimum": 0,
          "default": 0,
          "description": "Number of excluded files"
        },
        "budget_utilization": {
          "type": "number",
          "minimum": 0,
          "maximum": 100,
          "default": 0,
          "description": "Percentage of token budget used"
        }
      }
    },
    "FlightPlan": {
      "type": "object",
      "description": "Reused from Layer 1 - see flight-plan-schema.md",
      "properties": {
        "budget": {
          "type": "integer",
          "exclusiveMinimum": 0,
          "default": 20000
        },
        "focus": {
          "type": "object",
          "nullable": true
        },
        "verbosity": {
          "type": "array",
          "items": { "type": "object" }
        },
        "custom_queries": {
          "type": "array",
          "items": { "type": "object" }
        }
      }
    }
  }
}
```

## State Access Patterns

### Reading State (in InstructionProvider or Plugin)

```python
from google.adk.agents.readonly_context import ReadonlyContext
from repo_map.navigator.state import NavigatorState

def get_navigator_state(context: ReadonlyContext) -> NavigatorState:
    """Deserialize NavigatorState from session.state."""
    state_dict = dict(context.state)
    navigator_dict = state_dict.get("navigator", {})
    return NavigatorState.model_validate(navigator_dict)
```

### Writing State (in Tools)

```python
from google.adk.tools import ToolContext
from repo_map.navigator.state import NavigatorState

def update_navigator_state(context: ToolContext, state: NavigatorState) -> None:
    """Serialize and persist NavigatorState to session.state."""
    context.state["navigator"] = state.model_dump(mode="json")
```

## Example Serialized State

```json
{
  "navigator": {
    "user_task": "Refactor the auth middleware",
    "repo_path": "/home/user/project",
    "execution_mode": "autonomous",
    "budget_config": {
      "max_spend_usd": 2.0,
      "current_spend_usd": 0.0135,
      "model_pricing_rates": {
        "model_name": "gemini-2.0-flash",
        "input_per_million": 0.075,
        "output_per_million": 0.30
      }
    },
    "flight_plan": {
      "budget": 20000,
      "focus": null,
      "verbosity": [
        { "pattern": "src/auth/**", "level": 4 },
        { "pattern": "tests/**", "level": 1 }
      ],
      "custom_queries": []
    },
    "decision_log": [
      {
        "step": 1,
        "action": "update_flight_plan",
        "reasoning": "Initial scan complete. Zooming in on src/auth/ which contains authentication logic.",
        "config_diff": {
          "verbosity": [{ "pattern": "src/auth/**", "level": 4 }]
        },
        "timestamp": "2025-12-31T10:30:00Z"
      }
    ],
    "map_metadata": {
      "total_tokens": 8500,
      "file_count": 42,
      "focus_areas": ["src/auth/"],
      "excluded_count": 120,
      "budget_utilization": 42.5
    },
    "interactive_pause": false,
    "exploration_complete": false,
    "reasoning_summary": ""
  }
}
```
