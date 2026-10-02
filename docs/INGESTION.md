# Study and ingestion

Lean v1 supports individual local text sources through the synchronous Python SDK. It
does not provide a folder-ingestion CLI or recursive repository scanner.

| Input | Status | Current mechanism |
| --- | --- | --- |
| Plain text | Stable public | SDK `remember` or MCP `syune_remember` |
| TXT | Stable public | SDK Study |
| Markdown | Stable public | SDK Study |
| Text-based PDF | Stable public | SDK Study using `pypdf` |
| Scanned/image-only PDF | Unsupported | No OCR |
| DOCX | Unsupported | No extractor |
| HTML | Unsupported | No extractor |
| JSON | Unsupported as structured ingestion | No extractor |
| CSV | Unsupported | No extractor |
| Source code | Unsupported | No language-aware parser |
| Repository or folder | Unsupported | No recursive ingestion |
| URL/web page | Unsupported | No fetch/extraction path |
| Image, audio, video | Experimental/not productized | Provider-neutral perception structures only |

There is currently no `syune ingest ./folder` command or SDK equivalent.

## Stable Study example

Configure one or more approved absolute directories with `SYUNE_STUDY_ROOTS` or the
`[study] roots` configuration field. Then pass an absolute file path:

```python
from pathlib import Path
from syune import StudyRequest, Syune

state = Path("/absolute/path/to/state")
source = Path("/approved/library/notes.md")

with Syune.open(state_root=state) as client:
    result = client.study(StudyRequest(str(source)))
    print(result.data["source_id"])
```

Study automatically extracts TXT, Markdown, and text-based PDF content. It preserves
the filename and source URI, line or page locators, source/revision identifiers, and
provenance. Content fingerprints detect duplicates; the same content at another path is
recorded as an alias rather than duplicated. Changed content at the same path creates a
new source revision. Interrupted block materialization can resume.

Stable Study requires neither an LLM nor an external API. Study is not a tool on the
canonical Lean MCP server.

## Experimental perception

Provider-neutral structures for image regions, audio time ranges, and video time/frame
locators exist, but production perception providers and end-user configuration are not
included. Image, audio, and video ingestion is therefore experimental and not usable out
of the box.
