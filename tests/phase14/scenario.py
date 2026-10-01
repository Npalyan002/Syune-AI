"""Explicit local test host. Approval is supplied here, never by a runtime service."""
from contextlib import ExitStack
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from syune.core import *
from syune.memory import SQLiteMemoryRepository, Observation, Association
from syune.study import StudyService, SqliteStudyRegistry
from syune.retrieval import InvertedSeedIndex, RetrievalService, RecallRequest, RecallCue
from syune.learning import SQLiteLearningStore, StorePlasticityView
from syune.cognition import CognitiveService, CognitiveRequest, ProfileRegistry, ProfileName
from syune.council import CouncilService, CouncilRequest, CouncilMemberSpec
from syune.executive import *


def pipeline(root, stack):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    source = root / 'source.txt'
    source.write_text('Amber safety requirement\n\nAmber outcome verification', encoding='utf-8')
    memory = stack.enter_context(SQLiteMemoryRepository(root / 'memory.sqlite3'))
    study = stack.enter_context(SqliteStudyRegistry(root / 'study.sqlite3'))
    learning = stack.enter_context(SQLiteLearningStore(root / 'learning.sqlite3'))
    trace = 'phase14-local-e2e'
    studied = StudyService(study, memory, root).study(source)
    observations = tuple(x for x in memory.iter_entities() if isinstance(x, Observation))
    # Explicit synthetic relation, fixture input rather than automatic semantic learning.
    memory.add_association(Association(AssociationId.new(), observations[0].id, observations[1].id,
        'supports', observations[0].provenance, Confidence(.5), utc_now(), .7))
    canonical = memory.iter_entities()
    index = InvertedSeedIndex(memory)
    index.rebuild()
    retrieval = RetrievalService(memory, index, plasticity=StorePlasticityView(learning))
    recalled = retrieval.recall(RecallRequest(RecallCue(text='Amber', correlation_id=trace)))
    cognitive_service = CognitiveService(memory, retrieval)
    request = CognitiveRequest(CognitiveRequestId.new(), text='Amber', correlation_id=trace)
    cognitive = cognitive_service.process(request)
    profiles = ProfileRegistry()
    members = tuple(CouncilMemberSpec(profiles.by_name(p).id) for p in (ProfileName.GENERAL, ProfileName.SYSTEMS))
    council = CouncilService(cognitive_service).run(CouncilRequest(CouncilRequestId.new(), request, members))
    goal = Goal(GoalId.new(), 'update sandbox file', ('file verified',), source=GoalSource.TEST, correlation_id=trace)
    planner = ExecutiveService()
    planned = planner.plan(ExecutiveRequest(ExecutiveRequestId.new(), goal, cognitive, council, correlation_id=trace))
    return dict(root=root, source=source, memory=memory, registry=study, learning=learning,
        studied=studied, observations=observations, canonical=canonical, index=index,
        retrieval=retrieval, recalled=recalled, cognitive=cognitive, cognitive_service=cognitive_service,
        council=council, goal=goal, planner=planner, planned=planned, trace=trace)


def bind_sandbox(context):
    """Test host reviews and binds the proposed UPDATE to an explicit local sandbox.

    The three-step generic L2 draft remains retained in its original repository.
    Host-reviewed sandbox plan v2 records completed manual prerequisites and preserves
    the goal, context, risks and evidence. This is explicit fixture input, not replanning.
    """
    planned = context['planned']
    original = next(p for s in planned.plan.steps for p in s.action_proposals if p.action_type is ActionType.UPDATE)
    proposal = replace(original, id=ActionProposalId.new(), parameters=(('path','result.txt'),('content','verified amber'),('operation','write'),('mode','')),
        target_descriptor='sandbox:result.txt', side_effect_class=SideEffectClass.LOCAL_REVERSIBLE, estimated_risk=RiskLevel.MEDIUM)
    step = next(s for s in planned.plan.steps if original in s.action_proposals)
    step = replace(step, dependencies=(), action_proposals=(proposal,), status=StepStatus.REQUIRES_APPROVAL)
    checkpoint = PlanCheckpoint(PlanCheckpointId.new(), step.id, 'host confirms manual prerequisites and exact local scope', True, ('scope reviewed',))
    plan = replace(planned.plan, version=2, prior_version=1, revision_reason='explicit test-host sandbox binding after manual review',
        steps=(step,), dependencies=(), checkpoints=(checkpoint,), status=PlanStatus.REQUIRES_APPROVAL)
    envelope = context['planner']._envelope(plan)
    plans = InMemoryPlanRepository()
    plans.save(plan, None, envelope)
    descriptor = RuntimeCapabilityDescriptor(proposal.capability_requirement.id, 'LOCAL_SANDBOX_WRITE', ActionType.UPDATE, '1',
        CapabilityStatus.AVAILABLE, CapabilityHealth.HEALTHY, SideEffectClass.LOCAL_REVERSIBLE,
        ('path','content','operation','mode'), ('path','content','operation','mode'), IdempotencyMode.REQUIRED,
        RollbackMode.REQUIRES_APPROVAL, VerificationMode.READ_BACK, ApprovalKind.HUMAN, RiskLevel.MEDIUM,
        'SYUNE_EXECUTION_SANDBOX', 'local-file', '1', 'Phase14 explicit test host')
    adapter = LocalSandboxFileAdapter(context['root'] / 'sandbox')
    capabilities = CapabilityRegistry()
    capabilities.register(descriptor, adapter)
    store = SQLiteExecutionRepository(context['root'] / 'execution.sqlite3')
    runtime = SupervisedExecutiveService(plans, capabilities, store)
    budget = RuntimeBudget()
    hashes = ((proposal.id, parameter_hash(proposal)),)
    fp = approval_fingerprint(plan.id, plan.version, (proposal.id,), hashes, RiskLevel.MEDIUM, (SideEffectClass.LOCAL_REVERSIBLE,), budget)
    now = datetime.now(timezone.utc)
    token = ApprovalToken(ApprovalTokenId.new(), ApprovalSource.TEST, RuntimeApprovalStatus.VALID, plan.id, plan.version, envelope.id,
        (proposal.id,), hashes, RiskLevel.MEDIUM, (SideEffectClass.LOCAL_REVERSIBLE,), budget, now-timedelta(seconds=1),
        now+timedelta(hours=1), 'phase14-external-test-host', fp, True)
    request = ExecutionRequest(ExecutionRequestId.new(), plan.id, plan.version, envelope.id, (proposal.id,), token,
        budget, satisfied_checkpoint_ids=(checkpoint.id,), correlation_id=context['trace'])
    context.update(runtime=runtime, execution_store=store, execution_request=request, adapter=adapter,
        execution_plan=plan, envelope=envelope, proposal=proposal, descriptor=descriptor)
    return context
