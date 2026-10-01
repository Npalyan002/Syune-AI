param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)
$ErrorActionPreference = 'Stop'
$failures = [System.Collections.Generic.List[string]]::new()
$requiredDocs = @(
    'README.md','QUICKSTART.md','CONFIGURATION.md','LOCAL_OPERATIONS.md',
    'PUBLIC_API_V1.md','PYTHON_SDK.md','MCP_V1.md','HOST_INTEGRATION_PROTOCOL_V1.md',
    'COMPATIBILITY_MATRIX.md','known_limitations.md','threat_model.md',
    'architecture/LEAN_V1_ARCHITECTURE.md','architecture/MODEL_GATEWAY.md',
    'operations/model-gateway-policy.md','operations/observability.md','operations/recovery.md',
    'security/model-gateway-data-policy.md','benchmarks/LEAN_V1_VALIDATION.md',
    'benchmarks/HISTORICAL_EVALUATION_SUMMARY.md','research/README.md','release/v1.0.0.md'
)
$modules = @(
    'core','memory','study','retrieval','cognition','domains','council',
    'executive','gateway','providers','storage','events','governance',
    'telemetry','evals','learning'
)
foreach ($name in $requiredDocs) {
    if (-not (Test-Path -LiteralPath (Join-Path $RepositoryRoot "docs/$name") -PathType Leaf)) {
        $failures.Add("Missing canonical document: $name")
    }
}
foreach ($name in $modules) {
    $modulePath = Join-Path $RepositoryRoot "src/syune/$name"
    if (-not (Test-Path -LiteralPath (Join-Path $modulePath 'README.md') -PathType Leaf)) {
        $failures.Add("Missing module boundary: $name")
    }
}
$adrRoot = Join-Path $RepositoryRoot 'docs/ADR'
foreach ($name in @('ADR-0004-provider-agnostic-model-gateway.md','ADR-0005-study-idempotency-and-provenance.md','ADR-0009-runtime-language.md','ADR-0010-observation-memory-entity.md')) {
    $path = Join-Path $adrRoot $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or (Get-Content -LiteralPath $path -Raw) -notmatch 'Status:.*ACCEPTED') {
        $failures.Add("Current accepted ADR missing or ambiguous: $name")
    }
}
$sourceFiles = @(Get-ChildItem -LiteralPath (Join-Path $RepositoryRoot 'src') -Recurse -File | Where-Object { $_.FullName -notmatch '[\/]__pycache__[\/]' -and $_.Extension -ne '.pyc' })
$allowedCode = @(
    'src/syune/__init__.py',
    'src/syune/quickstart.py',
    'src/syune/api/__init__.py','src/syune/api/model.py','src/syune/api/errors.py','src/syune/api/version.py','src/syune/api/capabilities.py','src/syune/api/serialization.py',
    'src/syune/sdk/__init__.py','src/syune/sdk/client.py','src/syune/sdk/session.py',
    'src/syune/product/__init__.py','src/syune/product/config.py','src/syune/product/schema.py','src/syune/product/state.py','src/syune/product/runtime.py',
    'src/syune/cli/__init__.py','src/syune/cli/app.py',
    'src/syune/evals/__init__.py','src/syune/evals/model.py','src/syune/evals/runner.py',
    'src/syune/evals/metrics.py','src/syune/evals/regression.py','src/syune/evals/reporting.py','src/syune/evals/invariants.py',
    'src/syune/core/__init__.py', 'src/syune/core/primitives.py',
    'src/syune/memory/__init__.py', 'src/syune/memory/model.py',
    'src/syune/memory/repository.py', 'src/syune/memory/sqlite_repository.py',
    'src/syune/study/__init__.py', 'src/syune/study/model.py',
    'src/syune/study/errors.py', 'src/syune/study/parsers.py',
    'src/syune/study/diff.py', 'src/syune/study/registry.py',
    'src/syune/study/encoder.py', 'src/syune/study/service.py',
    'src/syune/retrieval/__init__.py', 'src/syune/retrieval/model.py',
    'src/syune/retrieval/index.py', 'src/syune/retrieval/service.py',
    'src/syune/gateway/mcp/__init__.py', 'src/syune/gateway/mcp/__main__.py',
    'src/syune/gateway/mcp/server.py',
    'src/syune/learning/__init__.py','src/syune/learning/model.py',
    'src/syune/learning/errors.py','src/syune/learning/policy.py',
    'src/syune/learning/store.py','src/syune/learning/service.py',
    'src/syune/cognition/__init__.py','src/syune/cognition/model.py',
    'src/syune/cognition/errors.py','src/syune/cognition/inference.py','src/syune/cognition/metacognition.py','src/syune/cognition/profiles.py','src/syune/cognition/service.py',
    'src/syune/perception/__init__.py','src/syune/perception/model.py','src/syune/perception/errors.py',
    'src/syune/perception/inspect.py','src/syune/perception/providers.py','src/syune/perception/router.py',
    'src/syune/council/__init__.py','src/syune/council/model.py','src/syune/council/errors.py',
    'src/syune/council/analysis.py','src/syune/council/synthesis.py','src/syune/council/service.py',
    'src/syune/executive/__init__.py','src/syune/executive/model.py','src/syune/executive/errors.py',
    'src/syune/executive/planner.py','src/syune/executive/policy.py','src/syune/executive/validation.py','src/syune/executive/service.py',
    'src/syune/executive/runtime_model.py','src/syune/executive/approval_runtime.py','src/syune/executive/capabilities.py',
    'src/syune/executive/runtime_gate.py','src/syune/executive/verification.py','src/syune/executive/execution_store.py','src/syune/executive/execution.py'
)
foreach ($file in $sourceFiles) {
    if ($file.Name -eq 'README.md') { continue }
    $relative = $file.FullName.Substring($RepositoryRoot.TrimEnd('\').Length + 1).Replace('\', '/')
    $allowedSourcePattern = '^src/syune/(api|sdk|product|cli|evals|core|memory|study|retrieval|gateway/mcp|learning|cognition|perception|council|executive|audit|context|model_gateway)/[^/]+\.py$'
    if ($relative -notin @('src/syune/__init__.py','src/syune/quickstart.py','src/syune/release.py','src/syune/retrieval_integrations.py') -and
        $relative -notmatch $allowedSourcePattern) {
        $failures.Add("Unauthorized runtime source file: $relative")
        continue
    }
    $body = Get-Content -LiteralPath $file.FullName -Raw
    if ($relative -ne 'src/syune/retrieval_integrations.py' -and $relative -notlike 'src/syune/model_gateway/*' -and $relative -notlike 'src/syune/product/*' -and $relative -notlike 'src/syune/cli/*' -and $relative -notlike 'src/syune/api/*' -and $relative -notlike 'src/syune/sdk/*' -and $relative -notlike 'src/syune/evals/*' -and $relative -notlike 'src/syune/gateway/mcp/*' -and $relative -notlike 'src/syune/council/*' -and $relative -notlike 'src/syune/executive/*' -and
        $body -match '(?im)^\s*(from|import)\s+(syune\.(study|cognition|domains|council|executive|gateway|providers|storage)|openai|anthropic|langchain|chromadb|faiss|qdrant|neo4j|pinecone|mcp|requests|httpx|aiohttp|urllib|socket)(\b|\.)') {
        $failures.Add("Forbidden higher-layer/provider dependency: $relative")
    }
    if ($relative -like 'src/syune/gateway/mcp/*' -and
        $body -match '(?im)^\s*(from|import)\s+(openai|anthropic|langchain|requests|httpx|aiohttp|urllib|socket|subprocess|syune\.(providers|domains))\b') {
        $failures.Add("Forbidden gateway dependency: $relative")
    }
    if ($body -match 'ART-DEP-AI') {
        $failures.Add("Forbidden ART-DEP-AI coupling: $relative")
    }
    if ($relative -like 'src/syune/study/*' -and
        $body -match '(?i)\b(write_bytes|write_text|unlink|rmtree|os\.system|subprocess)\b') {
        $failures.Add("Study must not mutate source files or launch processes: $relative")
    }
    if ($relative -like 'src/syune/memory/*' -and
        $body -match '(?im)^\s*(from|import)\s+(syune\.study|sqlite3|sqlalchemy|psycopg|redis|neo4j|chromadb|faiss|qdrant|pinecone)\b' -and
        $relative -ne 'src/syune/memory/sqlite_repository.py') {
        $failures.Add("Memory model/contract must remain independent of Study and storage: $relative")
    }
    if ($relative -like 'src/syune/memory/*' -and $body -match '(?im)^\s*(from|import)\s+syune\.retrieval\b') {
        $failures.Add("Memory must remain independent of Retrieval: $relative")
    }
    if ($relative -like 'src/syune/retrieval/*' -and
        $body -match '(?i)\b(write_bytes|write_text|unlink|rmtree|os\.system|subprocess|put_many|add_association)\b') {
        $failures.Add("Recall must not mutate durable memory or launch processes: $relative")
    }
    if ($relative -like 'src/syune/memory/*' -and $body -match '(?im)^\s*(from|import)\s+syune\.learning\b') {
        $failures.Add("Memory must remain independent of Learning: $relative")
    }
    if ($relative -like 'src/syune/retrieval/*' -and $body -match '(?im)^\s*(from|import)\s+syune\.learning\b') {
        $failures.Add("Retrieval must consume only its PlasticityView contract: $relative")
    }
    if ($relative -like 'src/syune/learning/*' -and
        $body -match '(?im)^\s*(from|import)\s+(openai|anthropic|langchain|requests|httpx|aiohttp|urllib|socket|subprocess|syune\.(executive|providers|council|domains|gateway))\b') {
        $failures.Add("Forbidden learning dependency: $relative")
    }
    if ($relative -like 'src/syune/cognition/*' -and
        $body -match '(?im)^\s*(from|import)\s+(openai|anthropic|langchain|requests|httpx|aiohttp|urllib|socket|subprocess|syune\.(executive|providers|council|domains|gateway|learning))\b') {
        $failures.Add("Forbidden cognition dependency: $relative")
    }
    if ($relative -eq 'src/syune/cognition/profiles.py' -and
        $body -match '(?i)\b(sqlite3|MemoryRepository|LearningLedger|PlasticityOverlay|classifier|self[_-]tuning)\b') {
        $failures.Add("Profiles must remain static processing policy without storage or routing: $relative")
    }
    if ($relative -like 'src/syune/perception/*' -and $body -match '(?i)\b(requests|httpx|aiohttp|urllib|socket|subprocess|os\.system|face[_ ]recognition|biometric|speaker[_ ]identity|Claim\()\b') {
        $failures.Add("Perception must remain local/provider-neutral and non-epistemic: $relative")
    }
    if ($relative -like 'src/syune/council/*' -and $body -match '(?im)^\s*(from|import)\s+(openai|anthropic|langchain|requests|httpx|aiohttp|urllib|socket|subprocess|syune\.(study|learning|providers|gateway|executive))\b') {
        $failures.Add("Council must remain read-only, provider-free, and non-executive: $relative")
    }
    if ($relative -like 'src/syune/council/*' -and $body -match '(?i)\b(put_many|add_association|LearningSignal|study\(|dispatch_agent|control_core|execute_action|majority[_-]vote)\b') {
        $failures.Add("Council must not mutate, learn, dispatch, or assign majority truth: $relative")
    }
    if ($relative -like 'src/syune/executive/*' -and $body -match '(?im)^\s*(from|import)\s+(openai|anthropic|langchain|requests|httpx|aiohttp|urllib|socket|subprocess|mcp|syune\.(study|learning|gateway|providers))\b') {
        $failures.Add("Executive must remain planning-only and side-effect-free: $relative")
    }
    if ($relative -like 'src/syune/executive/*' -and $body -match '(?i)\b(def\s+(execute|run_action|dispatch|call_tool|call_agent|approve|authorize)\b|LearningSignal\s*\(|put_many\s*\(|add_association\s*\(|os\.system|subprocess\.|requests\.|httpx\.|control_core\s*\()') {
        $failures.Add("Executive must not execute, mutate, learn, dispatch, or self-approve: $relative")
    }
    if ($relative -like 'src/syune/executive/*' -and $body -match '(?i)\b(shell_exec|powershell_exec|bash_exec|python_eval|arbitrary_http|eval\s*\(|exec\s*\(|create_autonomous_goal|auto_replan|wildcard_approval|production_agent)\b') {
        $failures.Add("Supervised Executive contains forbidden generic or autonomous execution: $relative")
    }
    if ($body -match '(?im)^\s*(from|import)\s+(sqlalchemy|psycopg|redis|neo4j|chromadb|faiss|qdrant|pinecone)\b') {
        $failures.Add("Forbidden database/provider dependency: $relative")
    }
    if ($body -match '(?i)\b(dispatch_agent|agent_dispatch|execute_action|vector_search|semantic_search|spreading_activation|study_ingest|ingest_document)\b') {
        $failures.Add("Forbidden Phase 02 behavior: $relative")
    }
}
foreach ($name in @('domains','providers','storage')) {
    if (@(Get-ChildItem -LiteralPath (Join-Path $RepositoryRoot "src/syune/$name") -Filter '*.py' -File).Count -gt 0) {
        $failures.Add("Future subsystem must remain inactive: $name")
    }
}
$gatewayCode = Get-Content -LiteralPath (Join-Path $RepositoryRoot 'src/syune/gateway/mcp/server.py') -Raw
$expectedTools = @('syune_health','syune_status','syune_capabilities','syune_source_status','syune_memory_get','syune_recall','syune_cognize','syune_council','syune_plan','syune_study_source')
$registeredTools = @([regex]::Matches($gatewayCode, '@server\.tool\(name="([^"]+)"') | ForEach-Object { $_.Groups[1].Value })
if (@(Compare-Object ($expectedTools | Sort-Object) ($registeredTools | Sort-Object)).Count -gt 0) {
    $failures.Add('MCP tool registry differs from approved allowlist')
}
if ($gatewayCode -match '(?i)\b(agent_dispatch|control_core|execute_plan|shell_tool|arbitrary_file_read)\b') {
    $failures.Add('Forbidden execution capability in MCP gateway')
}
$publicInit = Get-Content -LiteralPath (Join-Path $RepositoryRoot 'src/syune/__init__.py') -Raw
if ($publicInit -match '(SQLite|Repository|Store|Adapter|SupervisedExecutiveService|execute_approved)') {
    $failures.Add('Top-level public exports expose internal storage or execution implementation')
}
$publicRuntime = @(
    (Get-Content -LiteralPath (Join-Path $RepositoryRoot 'src/syune/api/__init__.py') -Raw),
    (Get-Content -LiteralPath (Join-Path $RepositoryRoot 'src/syune/sdk/__init__.py') -Raw)
) -join "`n"
if ($publicRuntime -match '(SQLite|Repository|Store|Adapter|SupervisedExecutiveService)') {
    $failures.Add('Public API namespace exposes internal repository/store implementation')
}
$productConfig = Get-Content -LiteralPath (Join-Path $RepositoryRoot 'src/syune/product/config.py') -Raw
if ($productConfig -notmatch 'learning:\s*bool\s*=\s*False' -or $productConfig -notmatch 'research_cognition:\s*bool\s*=\s*False') {
    $failures.Add('Experimental learning and research cognition must remain disabled by default')
}
foreach ($path in @('pyproject.toml','uv.lock','contracts/schemas/public/v1','src/syune/product','src/syune/api','src/syune/sdk','src/syune/model_gateway')) {
    if (-not (Test-Path -LiteralPath (Join-Path $RepositoryRoot $path) -PathType Leaf)) {
        if (-not (Test-Path -LiteralPath (Join-Path $RepositoryRoot $path) -PathType Container)) {
            $failures.Add("Missing Lean v1 product boundary: $path")
        }
    }
}
$activeNames = @(Get-ChildItem -LiteralPath $RepositoryRoot -File) + $sourceFiles
foreach ($file in $activeNames) {
    if ($file.Name -match '(?i)cognitive[_-]system|brain[_-]system|step\d{2}') {
        $failures.Add("Naming drift: $($file.FullName)")
    }
}
$readme = Get-Content -LiteralPath (Join-Path $RepositoryRoot 'README.md') -Raw
if ($readme -notmatch 'Research cognition and learning are disabled by default' -or $readme -notmatch 'experimental, retained for compatibility, and disabled by default') {
    $failures.Add('Root README lacks the explicit disabled-by-default research boundary')
}
$configFiles = @(Get-ChildItem -LiteralPath (Join-Path $RepositoryRoot 'config') -Recurse -File)
foreach ($file in $configFiles) {
    if ($file.Name -ne 'README.md') {
        $failures.Add("Unexpected active configuration file: $($file.FullName)")
    }
}
if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    exit 1
}
Write-Output 'SYUNE Lean v1 architecture boundary checks: PASS'
