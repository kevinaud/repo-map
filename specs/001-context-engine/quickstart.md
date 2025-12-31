# Quickstart: Context Engine Implementation

**Date**: 2025-12-31  
**Feature**: 001-context-engine

---

## Implementation Sequence

The implementation should proceed in this order to ensure each phase builds on tested foundations.

### Phase 1: Foundation (Weeks 1-2)

**Goal**: Core data structures and configuration loading.

#### 1.1 FlightPlan Model
- Create `repo_map/core/flight_plan.py`
- Implement Pydantic models: `FlightPlan`, `Focus`, `VerbosityRule`, etc.
- Add YAML loading with validation
- **Test**: Unit tests for valid/invalid configs

```python
# Key implementation
from pydantic import BaseModel, Field, model_validator

class FlightPlan(BaseModel):
    budget: int = Field(default=20000, gt=0)
    focus: Focus | None = None
    verbosity: list[VerbosityRule] = Field(default_factory=list)
    # ...
```

#### 1.2 Cost Calculation Module
- Create `repo_map/core/cost.py`
- Implement `estimate_tokens(text: str) -> int`
- Implement `calculate_file_costs(file_path, content) -> dict[VerbosityLevel, int]`
- **Test**: Unit tests with known file sizes

#### 1.3 CLI Extensions (Minimal)
- Add `--config` flag to `app.py`
- Wire FlightPlan loading to existing pipeline
- **Test**: E2E test with basic YAML config

### Phase 2: Multi-Resolution Extraction (Weeks 3-4)

**Goal**: Tiered tree-sitter query system.

#### 2.1 Query Reorganization
- Create `python-structure.scm` (Level 2)
- Create `python-interface.scm` (Level 3)
- Create `markdown-structure.scm` (Level 2)
- Create `markdown-interface.scm` (Level 3)
- **Test**: Unit tests comparing query outputs

#### 2.2 Dynamic Query Loading
- Modify `tags.py` to accept verbosity level parameter
- Implement `get_scm_fname(lang, level)` → select appropriate query
- Extract sections with line ranges
- **Test**: Unit tests for each verbosity level

```python
# Key modification in tags.py
def get_tags_from_code(
    fname: str,
    rel_fname: str,
    code: str,
    verbosity: VerbosityLevel = VerbosityLevel.STRUCTURE,
) -> Iterator[Tag]:
    ...
```

#### 2.3 Section Extraction
- Enhance `Tag` to include line ranges
- Implement section boundary detection
- **Test**: Unit tests with multi-class files

### Phase 3: Focus Boosting (Week 5)

**Goal**: PageRank personalization for symbol/path boosting.

#### 3.1 Personalization Integration
- Modify `RepoMap._get_ranked_tags()` to accept `focus_boosts` parameter
- Build personalization vector from FlightPlan focus config
- Integrate with `nx.pagerank()` call
- **Test**: Unit tests verifying boost effects

```python
# Key modification in repomap.py
def _get_ranked_tags(
    self,
    fnames: list[str],
    focus_boosts: dict[str, float] | None = None,
    progress: Callable[[str], None] | None = None,
) -> list[Tag | tuple[str]]:
    ...
    personalization = self._build_personalization(G, focus_boosts)
    ranked = nx.pagerank(G, personalization=personalization, ...)
```

#### 3.2 Symbol-to-File Resolution
- Implement symbol name → file path mapping
- Match Focus symbols against extracted definitions
- **Test**: E2E test with symbol boosting

### Phase 4: Rendering Engine (Weeks 6-7)

**Goal**: Budget-aware output composition.

#### 4.1 ContextRenderer Class
- Create `repo_map/core/renderer.py`
- Implement verbosity rule matching (glob patterns)
- Implement section-level verbosity matching
- **Test**: Unit tests for pattern matching

```python
# Key class
class ContextRenderer:
    def __init__(self, flight_plan: FlightPlan):
        self.plan = flight_plan
    
    def render(self, files: list[FileNode]) -> RenderResult:
        ...
    
    def get_verbosity(self, file_path: str) -> VerbosityLevel:
        ...
```

#### 4.2 Output Generation
- Implement rendering at each verbosity level
- Add cost annotation headers (when enabled)
- Add budget warning/error handling
- **Test**: E2E tests comparing output formats

#### 4.3 Budget Enforcement
- Implement soft mode (warning)
- Implement strict mode (error with details)
- **Test**: E2E tests exceeding budget

### Phase 5: CLI Completion (Week 8)

**Goal**: Full CLI integration and polish.

#### 5.1 New Flags
- Implement `--strict` flag
- Implement `--show-costs` flag
- Implement `-v pattern:level` shorthand
- Implement `--focus pattern` shorthand
- **Test**: E2E tests for all flag combinations

#### 5.2 Error Handling
- Implement detailed error messages
- Add exit codes
- **Test**: E2E tests for error scenarios

#### 5.3 Documentation
- Update CLI help text
- Update README with examples
- Add example flight plans

### Phase 6: Testing & Polish (Week 9)

**Goal**: Comprehensive test coverage and performance validation.

#### 6.1 Integration Tests
- Create sample repository fixture
- Test full pipeline with various flight plans
- Verify cost estimation accuracy (<10% error)

#### 6.2 Performance Testing
- Test with 10,000+ file repository
- Verify <30 second execution time
- Profile and optimize if needed

#### 6.3 Edge Cases
- Binary file handling
- Files without AST parser
- Malformed markdown
- Empty directories

---

## File Creation Order

```
1. repo_map/core/flight_plan.py      # FlightPlan model
2. tests/unit/test_flight_plan.py    # Validation tests
3. repo_map/core/cost.py             # Cost utilities
4. tests/unit/test_cost.py           # Cost tests
5. repo_map/core/queries/.../python-structure.scm
6. repo_map/core/queries/.../python-interface.scm
7. repo_map/core/queries/.../markdown-structure.scm
8. repo_map/core/queries/.../markdown-interface.scm
9. (modify) repo_map/core/tags.py    # Tiered loading
10. tests/unit/test_tags_verbosity.py
11. (modify) repo_map/core/repomap.py # Personalization
12. tests/unit/test_boosting.py
13. repo_map/core/renderer.py        # ContextRenderer
14. tests/unit/test_renderer.py
15. (modify) repo_map/cli/app.py     # New flags
16. (modify) repo_map/mapper.py      # Wire components
17. tests/fixtures/sample-repo/      # Test fixtures
18. tests/fixtures/flight-plans/     # Sample configs
19. tests/integration/test_context_engine.py
```

---

## Key Dependencies

| Module | Depends On |
|--------|------------|
| `flight_plan.py` | pydantic, PyYAML |
| `cost.py` | (none) |
| `tags.py` (modified) | flight_plan.py |
| `repomap.py` (modified) | tags.py |
| `renderer.py` | flight_plan.py, cost.py |
| `mapper.py` (modified) | flight_plan.py, renderer.py |
| `app.py` (modified) | mapper.py |

---

## Verification Checkpoints

After each phase, verify:

- [ ] `make quality` passes
- [ ] `make test-unit` passes
- [ ] New code has type hints
- [ ] New functions have docstrings
- [ ] Error cases are handled gracefully
