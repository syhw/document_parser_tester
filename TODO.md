# TODO - VLM Document Testing Library

## 1. CLEANUP & SIMPLIFICATION

### Critical (Do This Week)

| Issue | Files | Effort | Impact |
|-------|-------|--------|--------|
| **6 bare `except:` clauses** | `docling_parser.py`, `pipeline_comparison.py` | 30 min | Silent failures → visible errors |
| **Dead VLM stubs** | `vlm_parser.py` (2 NotImplementedError) | 15 min | Remove confusion |
| **Duplicate markdown parsing** | `marker_parser.py`, `docling_parser.py` | 45 min | -60 lines duplication |

### High Priority (Next Sprint)

| Issue | Current State | Proposed | Effort |
|-------|--------------|----------|--------|
| **8 confidence classes** | `ConfidenceLevel`, `TextQualityMetrics`, `LayoutMetrics`, `TableConfidenceMetrics`, `FigureConfidenceMetrics`, `PageConfidence`, `ExtractionConfidence`, etc. | Merge to 3-4 classes | 2h |
| **4 config classes** | `MarkerConfig`, `DoclingConfig`, `TableSettings`, `AdaptivePipelineConfig` | Base `ParserConfig` class | 1.5h |
| **3 comparison methods** | Scattered in `marker_parser`, `docling_parser`, `pipeline_comparison` | Unified `PipelineComparator` | 1h |
| **Inconsistent ID generation** | 4 different formats across parsers | `IDGenerator` utility | 1h |

### Suggested File Merges

```
BEFORE                              AFTER
────────────────────────────────────────────────────────────
vlm_analyzer.py (325 lines)    →   Keep (VLM client)
vlm_parser.py (314 lines)      →   Simplify (remove dead stubs)
confidence.py (226 lines)      →   Reduce to ~150 lines
confidence_calculator.py (518) →   Split into smaller modules
adaptive_parser.py (460 lines) →   Extract EscalationStrategy class
```

### Files to Add

```
vlm_doc_test/
├── utils/
│   ├── markdown_utils.py      # Extract shared markdown parsing
│   ├── id_generator.py        # Consistent ID generation
│   └── exceptions.py          # Custom exceptions
└── parsers/
    └── base_config.py         # Base ParserConfig class
```

---

## 2. PHASE 4 & BEYOND ROADMAP

### Phase 4: Production Hardening (Current)
**Goal**: Make the library reliable for real-world documents

| Feature | Status | Priority |
|---------|--------|----------|
| Adaptive parser with confidence escalation | ✅ Done | - |
| Confidence scoring system | ✅ Done | - |
| Webapp for visual comparison | ✅ Done | - |
| Error handling cleanup | 🔲 Pending | HIGH |
| Caching layer for VLM responses | 🔲 Pending | HIGH |
| Batch processing with progress | 🔲 Pending | MEDIUM |

### Phase 5: Scale & Performance
**Goal**: Handle 100+ documents efficiently

| Feature | Description | Priority |
|---------|-------------|----------|
| **Parallel parsing** | Process multiple PDFs concurrently | HIGH |
| **Result caching** | SQLite/Redis cache for VLM responses | HIGH |
| **Incremental processing** | Resume from checkpoint on failure | MEDIUM |
| **Memory optimization** | Stream large PDFs, limit page buffers | MEDIUM |
| **Metrics dashboard** | Track parsing success rates, confidence distributions | LOW |

### Phase 6: Advanced Extraction
**Goal**: Handle complex document types

| Feature | Description | Priority |
|---------|-------------|----------|
| **GROBID integration** | Academic paper structure extraction (Docker) | HIGH |
| **DePlot for charts** | Convert plots to data tables (GPU) | MEDIUM |
| **OCR fallback** | Tesseract/EasyOCR for scanned PDFs | MEDIUM |
| **Multi-language** | Support non-English documents | LOW |

### Phase 7: Ground Truth & Benchmarking
**Goal**: Measure and improve accuracy

| Feature | Description | Priority |
|---------|-------------|----------|
| **Ground truth dataset** | 50 manually annotated documents | HIGH |
| **Accuracy metrics** | Precision/recall for each field | HIGH |
| **Parser leaderboard** | Compare PyMuPDF vs Marker vs Docling vs VLM | MEDIUM |
| **Regression testing** | Detect quality degradation on updates | MEDIUM |

---

## 3. 100 DOCUMENT PARSING PLAN

### Document Collection Strategy

| Category | Count | Source | Complexity |
|----------|-------|--------|------------|
| **Academic Papers** | 30 | arXiv, PubMed, ACL Anthology | HIGH (tables, figures, equations, citations) |
| **Technical Docs** | 20 | GitHub READMEs, API docs, RFCs | MEDIUM (code blocks, diagrams) |
| **Books/Chapters** | 15 | Project Gutenberg, O'Reilly samples | HIGH (long-form, TOC, footnotes) |
| **News/Blog** | 15 | Saved web pages as PDF | LOW-MEDIUM (ads, navigation) |
| **Reports/Whitepapers** | 10 | Company reports, research reports | MEDIUM (charts, tables) |
| **Presentations** | 10 | SlideShare PDFs, conference slides | MEDIUM (layout-heavy) |

### Proposed Directory Structure

```
vlm_doc_test/tests/fixtures/documents/
├── academic_papers/
│   ├── arxiv/           # 10 CS papers
│   ├── pubmed/          # 10 medical papers
│   └── humanities/      # 10 non-STEM papers
├── technical_docs/
│   ├── api_docs/        # 10 API documentation
│   └── tutorials/       # 10 how-to guides
├── books/
│   ├── fiction/         # 5 novel chapters
│   └── nonfiction/      # 10 textbook chapters
├── web_content/
│   ├── news/            # 10 news articles
│   └── blogs/           # 5 blog posts
├── reports/
│   └── business/        # 10 company reports
└── presentations/
    └── slides/          # 10 slide decks
```

### Execution Plan

**Week 1: Setup & Collection**
```bash
# Create collection script
python scripts/collect_documents.py \
  --arxiv 10 \
  --pubmed 10 \
  --gutenberg 5 \
  --output fixtures/documents/
```

**Week 2: Initial Parsing Run**
```python
# Batch parsing with all parsers
from vlm_doc_test.parsers import AdaptivePDFParser, BALANCED_PIPELINE

results = []
for doc_path in all_documents:
    parser = AdaptivePDFParser(config=BALANCED_PIPELINE)
    result = parser.parse(doc_path)
    results.append({
        "path": doc_path,
        "confidence": result.confidence.overall_score,
        "parser_used": result.final_parser.value,
        "duration": result.total_duration,
    })

# Save results
pd.DataFrame(results).to_csv("parsing_results.csv")
```

**Week 3: Analysis & Ground Truth**
- Identify 50 documents with lowest confidence
- Manually annotate 20 documents for ground truth
- Compare parser outputs to ground truth

**Week 4: Optimization**
- Tune confidence thresholds based on results
- Identify document types that need VLM escalation
- Build category-specific parsing profiles

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Parse success rate** | >95% | Documents without errors |
| **High confidence rate** | >70% | Documents with confidence ≥0.85 |
| **VLM escalation rate** | <20% | Documents requiring VLM |
| **Avg parse time** | <5s | Time per document (no VLM) |
| **Title extraction accuracy** | >90% | Compared to ground truth |
| **Table extraction accuracy** | >80% | Compared to ground truth |

### Infrastructure Needs

| Component | Purpose | Estimated Cost |
|-----------|---------|----------------|
| **Storage** | 100 PDFs (~500MB-2GB) | Local disk |
| **VLM API** | GLM-4V calls for escalation | ~$10-50 for 100 docs |
| **SQLite cache** | Store VLM responses | Free |
| **Progress tracking** | `tqdm` + JSON logs | Free |

---

## 4. COMPLETED ITEMS

- [x] Phase 0: Core schemas, PDF parser, equivalence checker
- [x] Phase 1: HTML parser, pytest framework, visual regression (SSIM)
- [x] Phase 2: Playwright web rendering, pdfplumber tables, web scraping
- [x] Phase 3: Marker parser, Docling parser, pipeline comparison, category validation
- [x] Phase 4 (partial): Adaptive parser, confidence scoring, webapp
