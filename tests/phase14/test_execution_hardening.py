from dataclasses import replace
from datetime import timedelta
import pytest
from test_supervised_execution import fixture
from syune.core import ExecutionRequestId, ApprovalTokenId
from syune.executive import *


@pytest.mark.parametrize("change", ["missing", "revoked", "stale", "future"])
def test_replay_revalidates_approval(tmp_path, change):
    runtime, request, adapter, store, *_ = fixture(tmp_path)
    try:
        assert runtime.execute_approved(request).status is RuntimeResultStatus.COMPLETED_VERIFIED
        token = request.approval
        if change == "missing": token = None
        if change == "revoked": token = replace(token, status=RuntimeApprovalStatus.REVOKED)
        if change == "stale": token = replace(token, plan_version=2)
        if change == "future": token = replace(token, issued_at=token.expires_at-timedelta(days=1))
        result = runtime.execute_approved(replace(request, approval=token))
        assert result.status is RuntimeResultStatus.EXECUTION_BLOCKED
        assert not result.receipts and adapter.calls == 1
    finally:
        store.close()


@pytest.mark.parametrize("change", ["revoked", "other_token", "stale", "missing"])
def test_rollback_requires_exact_fresh_original_authority(tmp_path, change):
    runtime, request, adapter, store, *_ = fixture(tmp_path)
    try:
        receipt = runtime.execute_approved(request).receipts[0]
        token = request.approval
        if change == "revoked": token = replace(token, status=RuntimeApprovalStatus.REVOKED)
        if change == "other_token": token = replace(token, id=ApprovalTokenId.new())
        if change == "stale": token = replace(token, plan_version=2)
        if change == "missing": token = None
        with pytest.raises(ExecutionError):
            runtime.rollback(replace(request, approval=token), receipt)
        assert (adapter.root / "case/value.txt").read_text() == "amber"
    finally:
        store.close()


def test_unclassified_post_effect_failure_never_blindly_retries(tmp_path):
    runtime, request, adapter, store, *_ = fixture(tmp_path)
    original = adapter.invoke
    def uncertain(invocation):
        original(invocation)
        raise OSError("private-content-must-not-be-logged")
    adapter.invoke = uncertain
    try:
        result = runtime.execute_approved(request)
        again = runtime.execute_approved(request)
        assert result.receipts[0].status is ExecutionStatus.UNKNOWN_OUTCOME
        assert not again.receipts and adapter.calls == 1
        assert "private-content" not in repr(result)
        assert runtime.recover_incomplete()[0].status is ExecutionStatus.SUCCEEDED_VERIFIED
        assert adapter.calls == 1
    finally:
        store.close()


def test_verification_failure_is_terminal_until_explicit_rollback(tmp_path):
    runtime, request, adapter, store, *_ = fixture(tmp_path, mode="verify_fail")
    try:
        assert runtime.execute_approved(request).receipts[0].status is ExecutionStatus.ROLLBACK_REQUIRED
        runtime.execute_approved(request)
        assert adapter.calls == 1
    finally:
        store.close()
