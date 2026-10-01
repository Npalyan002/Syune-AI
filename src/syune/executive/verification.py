from uuid import NAMESPACE_URL,uuid5
from syune.core import VerificationId
from .runtime_model import *
class OutcomeVerifier:
    def verify(self,descriptor,adapter,invocation,raw):
        if descriptor.verification_mode is VerificationMode.NONE_REQUIRED:return VerificationResult(VerificationId(uuid5(NAMESPACE_URL,invocation.idempotency_key+":verify")),VerificationStatus.NOT_REQUIRED,descriptor.verification_mode,"none","none",("capability declares no verification",))
        try:ok,observed=adapter.verify(invocation,raw)
        except Exception as exc:return VerificationResult(VerificationId(uuid5(NAMESPACE_URL,invocation.idempotency_key+":verify")),VerificationStatus.UNAVAILABLE,descriptor.verification_mode,"declared output",type(exc).__name__,( "verification unavailable",))
        return VerificationResult(VerificationId(uuid5(NAMESPACE_URL,invocation.idempotency_key+":verify")),VerificationStatus.PASSED if ok else VerificationStatus.FAILED,descriptor.verification_mode,"declared expected state",str(observed),("read-back matched",) if ok else ("read-back mismatch",))
