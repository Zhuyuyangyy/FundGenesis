"""
tests/regression/test_p2_benchmark.py
======================================
P2 ReflexMarket-Bench 标准化测试。

验证：
  P2.1: YAML 场景文件完整性与格式
  P2.2: BenchmarkRunner 批量运行与结果汇总
  P2.3: 标准化输出格式（JSON 结果 + artifacts 路径）
  P2.4: 全部 60 条 Benchmark 通过率
"""

import pytest
import os, sys, json, glob, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

BENCH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scenarios", "bench")


# ── P2.1: YAML 场景文件完整性 ────────────────────────────────

class TestBenchmarkYAMLIntegrity:
    """P2.1: 验证所有 YAML benchmark 文件的格式与完整性"""

    def _get_all_yaml_files(self):
        """获取所有 benchmark YAML 文件"""
        yaml_files = sorted(glob.glob(os.path.join(BENCH_DIR, "**", "*.yaml"), recursive=True))
        assert len(yaml_files) > 0, f"No YAML files found in {BENCH_DIR}"
        return yaml_files

    def test_total_benchmark_count(self):
        """应有 60 条 benchmark"""
        yaml_files = self._get_all_yaml_files()
        assert len(yaml_files) == 60, f"Expected 60 benchmarks, got {len(yaml_files)}"

    def test_category_distribution(self):
        """应有 6 个类别，数量正确"""
        categories = {}
        for yaml_path in self._get_all_yaml_files():
            parts = yaml_path.split(os.sep)
            for p in parts:
                if p.startswith(("A_", "B_", "C_", "D_", "E_", "F_")):
                    categories[p] = categories.get(p, 0) + 1
                    break

        expected = {
            "A_narrative": 12,
            "B_trust": 10,
            "C_reflexivity": 12,
            "D_risk": 10,
            "E_regulation": 10,
            "F_robustness": 6,
        }
        assert categories == expected, f"Category distribution mismatch: {categories}"

    def test_all_yaml_loadable(self):
        """所有 YAML 文件应可加载为 ScenarioConfig"""
        from core.scenario_config import ScenarioConfig
        for yaml_path in self._get_all_yaml_files():
            config = ScenarioConfig.from_yaml(yaml_path)
            assert config.id != "", f"Missing id in {yaml_path}"
            assert config.name != "", f"Missing name in {yaml_path}"
            assert config.steps > 0, f"Invalid steps in {yaml_path}"

    def test_all_yaml_have_expected_section(self):
        """所有 YAML 文件应有 expected 验收指标"""
        from core.scenario_config import ScenarioConfig
        for yaml_path in self._get_all_yaml_files():
            config = ScenarioConfig.from_yaml(yaml_path)
            # 至少有一个验收指标
            has_expected = any(v is not None for v in [
                config.expected.price_peak_min,
                config.expected.price_peak_max,
                config.expected.bubble_risk_peak_min,
                config.expected.bubble_risk_peak_max,
                config.expected.manipulation_risk_peak_min,
                config.expected.manipulation_risk_peak_max,
                config.expected.high_risk_steps_min,
                config.expected.high_risk_steps_max,
                config.expected.narrative_penetration_min,
            ])
            assert has_expected, f"No expected metrics in {yaml_path}"

    def test_all_yaml_have_seed(self):
        """所有 YAML 文件应有 seed 保证可复现"""
        from core.scenario_config import ScenarioConfig
        for yaml_path in self._get_all_yaml_files():
            config = ScenarioConfig.from_yaml(yaml_path)
            assert config.seed is not None, f"Missing seed in {yaml_path}"


# ── P2.2: BenchmarkRunner 功能 ───────────────────────────────

class TestBenchmarkRunner:
    """P2.2: 验证 BenchmarkRunner 的运行与判定功能"""

    def test_run_single_success(self):
        """单条 benchmark 应成功运行"""
        from core.benchmark_runner import BenchmarkRunner
        runner = BenchmarkRunner(output_dir=tempfile.mkdtemp())

        yaml_path = os.path.join(BENCH_DIR, "A_narrative", "A01_positive_narrative_bubble.yaml")
        result = runner.run_single(yaml_path)

        assert result.case_id == "A01"
        assert result.error is None
        assert "peak_manipulation_risk" in result.metrics
        assert "price_peak" in result.metrics
        assert "timeline" in result.artifacts
        assert "result" in result.artifacts

    def test_run_single_artifacts_saved(self):
        """运行后应生成 timeline.json 和 result.json"""
        from core.benchmark_runner import BenchmarkRunner

        output_dir = tempfile.mkdtemp()
        runner = BenchmarkRunner(output_dir=output_dir)

        yaml_path = os.path.join(BENCH_DIR, "A_narrative", "A01_positive_narrative_bubble.yaml")
        result = runner.run_single(yaml_path)

        assert os.path.exists(result.artifacts["timeline"])
        assert os.path.exists(result.artifacts["result"])

        # 验证 result.json 内容
        with open(result.artifacts["result"]) as f:
            saved = json.load(f)
        assert saved["case_id"] == "A01"
        assert "passed" in saved
        assert "metrics" in saved

    def test_run_single_validation_judgment(self):
        """应正确判定通过/失败"""
        from core.benchmark_runner import BenchmarkRunner
        runner = BenchmarkRunner(output_dir=tempfile.mkdtemp())

        yaml_path = os.path.join(BENCH_DIR, "A_narrative", "A01_positive_narrative_bubble.yaml")
        result = runner.run_single(yaml_path)

        # A01 应通过（price_peak_min=115, bubble_risk_peak_min=0.10）
        assert result.passed is True
        assert all(result.validation.values())

    def test_run_batch_generates_report(self):
        """批量运行应生成报告"""
        from core.benchmark_runner import BenchmarkRunner

        output_dir = tempfile.mkdtemp()
        runner = BenchmarkRunner(output_dir=output_dir)

        # 只运行 A 类（12条）以加快测试速度
        a_dir = os.path.join(BENCH_DIR, "A_narrative")
        report = runner.run_batch(a_dir)

        assert report.total == 12
        assert report.passed + report.failed + report.errored == 12
        assert "A_narrative" in report.by_category
        assert report.by_category["A_narrative"]["total"] == 12

        # 报告文件应保存
        report_path = os.path.join(output_dir, "bench_report.json")
        assert os.path.exists(report_path)

        with open(report_path) as f:
            saved = json.load(f)
        assert saved["total"] == 12

    def test_category_extraction(self):
        """应正确从路径提取类别"""
        from core.benchmark_runner import BenchmarkRunner
        runner = BenchmarkRunner(output_dir=tempfile.mkdtemp())

        assert runner._get_category("/path/to/A_narrative/A01.yaml") == "A_narrative"
        assert runner._get_category("/path/to/E_regulation/E01.yaml") == "E_regulation"
        assert runner._get_category("/path/to/F_robustness/F01.yaml") == "F_robustness"


# ── P2.3: 标准化输出格式 ─────────────────────────────────────

class TestBenchmarkOutputFormat:
    """P2.3: 验证标准化输出格式"""

    def test_result_json_structure(self):
        """result.json 应有标准结构"""
        from core.benchmark_runner import BenchmarkRunner
        runner = BenchmarkRunner(output_dir=tempfile.mkdtemp())

        yaml_path = os.path.join(BENCH_DIR, "A_narrative", "A01_positive_narrative_bubble.yaml")
        result = runner.run_single(yaml_path)

        with open(result.artifacts["result"]) as f:
            saved = json.load(f)

        required_keys = {"case_id", "name", "seed", "passed", "metrics", "validation"}
        assert required_keys.issubset(saved.keys())

    def test_timeline_json_structure(self):
        """timeline.json 应有标准结构"""
        from core.benchmark_runner import BenchmarkRunner
        runner = BenchmarkRunner(output_dir=tempfile.mkdtemp())

        yaml_path = os.path.join(BENCH_DIR, "A_narrative", "A01_positive_narrative_bubble.yaml")
        result = runner.run_single(yaml_path)

        with open(result.artifacts["timeline"]) as f:
            timeline = json.load(f)

        assert isinstance(timeline, list)
        assert len(timeline) > 0

        # 每个快照应有标准字段
        snap = timeline[0]
        required_keys = {"step", "market", "emotion", "risk"}
        assert required_keys.issubset(snap.keys())

    def test_benchmark_result_dataclass(self):
        """BenchmarkResult 应正确序列化"""
        from core.benchmark_runner import BenchmarkResult

        result = BenchmarkResult(
            case_id="TEST",
            name="test_case",
            category="A_narrative",
            seed=42,
            passed=True,
            metrics={"price_peak": 150.0},
            validation={"price_peak_min": True},
            artifacts={"timeline": "/tmp/timeline.json"},
            duration_sec=1.5,
        )

        d = result.to_dict()
        assert d["case_id"] == "TEST"
        assert d["passed"] is True
        assert d["metrics"]["price_peak"] == 150.0

    def test_benchmark_report_summary(self):
        """BenchmarkReport.summary_str() 应生成可读报告"""
        from core.benchmark_runner import BenchmarkReport

        report = BenchmarkReport(
            total=10, passed=8, failed=2, errored=0,
            pass_rate=80.0,
            by_category={"A_narrative": {"total": 10, "passed": 8, "failed": 2, "errored": 0}},
            results=[],
            timestamp="2026-01-01",
        )

        summary = report.summary_str()
        assert "Total: 10" in summary
        assert "Pass Rate: 80.0%" in summary
        assert "A_narrative" in summary


# ── P2.4: 全量通过率验证（抽样） ─────────────────────────────

class TestBenchmarkPassRate:
    """P2.4: 验证 benchmark 通过率"""

    def test_sample_benchmarks_pass(self):
        """抽样验证各类别至少一条 benchmark 通过"""
        from core.benchmark_runner import BenchmarkRunner
        runner = BenchmarkRunner(output_dir=tempfile.mkdtemp())

        # 每个类别选第一条
        samples = [
            ("A_narrative", "A01_positive_narrative_bubble.yaml"),
            ("B_trust", "B01_trust_formation.yaml"),
            ("C_reflexivity", "C01_self_reinforcing_loop.yaml"),
            ("D_risk", "D01_kol_coordination_detection.yaml"),
            ("E_regulation", "E01_no_intervention_baseline.yaml"),
            ("F_robustness", "F01_extreme_noise.yaml"),
        ]

        for category, filename in samples:
            yaml_path = os.path.join(BENCH_DIR, category, filename)
            result = runner.run_single(yaml_path)
            assert result.error is None, f"{category}/{filename} errored: {result.error}"
            assert result.passed, f"{category}/{filename} did not pass: {result.validation}"

    def test_reproducibility(self):
        """同一 benchmark 两次运行结果应一致（同 seed）"""
        from core.benchmark_runner import BenchmarkRunner

        runner1 = BenchmarkRunner(output_dir=tempfile.mkdtemp())
        runner2 = BenchmarkRunner(output_dir=tempfile.mkdtemp())

        yaml_path = os.path.join(BENCH_DIR, "A_narrative", "A01_positive_narrative_bubble.yaml")
        r1 = runner1.run_single(yaml_path)
        r2 = runner2.run_single(yaml_path)

        assert r1.metrics["price_peak"] == r2.metrics["price_peak"]
        assert r1.metrics["peak_manipulation_risk"] == r2.metrics["peak_manipulation_risk"]
        assert r1.passed == r2.passed
