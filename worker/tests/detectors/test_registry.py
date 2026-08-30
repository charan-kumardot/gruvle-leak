from app.detectors.base import DetectionContext
from app.detectors.registry import ALL_DETECTORS, run_all_detectors
from app.schemas.domain import DetectorStatus, LeakCategory


def test_all_ten_categories_registered():
    categories = {d.category for d in ALL_DETECTORS}
    assert categories == set(LeakCategory)


def test_stub_detectors_report_not_implemented_not_fake_findings():
    ctx = DetectionContext(scan_id="s1", business_id="b1", default_currency="INR", datasets=[])
    results = run_all_detectors(ctx)
    stub_categories = {LeakCategory.INVENTORY, LeakCategory.REFUND, LeakCategory.CUSTOMER,
                        LeakCategory.CONTRACT, LeakCategory.OPERATIONS}
    for r in results:
        if r.category in stub_categories:
            assert r.status == DetectorStatus.SKIPPED_NOT_IMPLEMENTED
            assert r.findings == []
            assert r.skip_reason


def test_a_failing_detector_does_not_take_down_the_whole_run(monkeypatch):
    from app.detectors.unbilled import UnbilledRevenueDetector

    def boom(self, ctx):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(UnbilledRevenueDetector, "detect", boom)
    ctx = DetectionContext(scan_id="s1", business_id="b1", default_currency="INR", datasets=[])
    results = run_all_detectors(ctx)

    failed = [r for r in results if r.category == LeakCategory.UNBILLED]
    assert len(failed) == 1
    assert failed[0].status == DetectorStatus.FAILED
    assert "simulated failure" in failed[0].errors[0]
    # every other detector still produced a result
    assert len(results) == len(ALL_DETECTORS)
