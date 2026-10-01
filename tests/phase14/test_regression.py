from syune.evals.model import RegressionBaseline,EvalMetric
from syune.evals.regression import compare


def test_regression_policy_counts_strict_latency_coarse_platform_explicit():
    baseline=RegressionBaseline('1','local',(EvalMetric('test_count',200),EvalMetric('error_count',0),EvalMetric('latency_ms',10)))
    assert not compare(baseline,(EvalMetric('test_count',201),EvalMetric('error_count',0),EvalMetric('latency_ms',14)),'local')
    assert len(compare(baseline,(EvalMetric('test_count',199),EvalMetric('error_count',1),EvalMetric('latency_ms',16)),'local'))==3
    assert compare(baseline,(),'other')==('platform differs: establish a comparable baseline',)
