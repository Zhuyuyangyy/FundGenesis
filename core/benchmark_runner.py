"""
core/benchmark_runner.py
==========================
P2.2 + P2.3: Benchmark 批量运行器 + 标准化输出。

功能：
  - 批量运行所有 YAML benchmark 场景
  - 自动判定通过/失败
  - 生成标准化 JSON 结果
  - 输出通过率报告

用法：
    python core/benchmark_runner.py --dir scenarios/bench --output outputs/bench_results.json
"""

import os, sys, json, time, glob
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.scenario_config import ScenarioConfig
from core.scenario_runner import ScenarioRunner


@dataclass
class BenchmarkResult:
    """单个 benchmark 的运行结果"""
    case_id: str
    name: str
    category: str
    seed: int
    passed: bool
    metrics: Dict[str, Any]
    validation: Dict[str, bool]
    artifacts: Dict[str, str]
    duration_sec: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkReport:
    """完整 benchmark 报告"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    errored: int = 0
    pass_rate: float = 0.0
    by_category: Dict[str, Dict[str, int]] = field(default_factory=dict)
    results: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def summary_str(self) -> str:
        lines = [
            "=" * 70,
            "ReflexMarket-Bench Results",
            "=" * 70,
            f"  Total: {self.total}  Passed: {self.passed}  Failed: {self.failed}  Errored: {self.errored}",
            f"  Pass Rate: {self.pass_rate:.1f}%",
            "",
            "  By Category:",
        ]
        for cat, stats in sorted(self.by_category.items()):
            rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            lines.append(f"    {cat:<30} {stats['passed']}/{stats['total']} ({rate:.0f}%)")

        lines.append("")
        lines.append("  Failed Cases:")
        for r in self.results:
            if not r["passed"] and r["error"] is None:
                failed_checks = [k for k, v in r["validation"].items() if not v]
                lines.append(f"    {r['case_id']} ({r['name']}): {failed_checks}")
        lines.append("")
        lines.append("  Errored Cases:")
        for r in self.results:
            if r["error"] is not None:
                lines.append(f"    {r['case_id']} ({r['name']}): {r['error'][:80]}")
        lines.append("=" * 70)
        return "\n".join(lines)


class BenchmarkRunner:
    """
    P2.2: Benchmark 批量运行器。
    """

    def __init__(self, output_dir: str = "outputs/bench"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def run_single(self, yaml_path: str) -> BenchmarkResult:
        """运行单个 benchmark"""
        start_time = time.time()

        try:
            config = ScenarioConfig.from_yaml(yaml_path)
            runner = ScenarioRunner(config)
            run_result = runner.run(verbose=False)
            results = run_result["results"]
            validation = run_result.get("validation", {})

            # 判定通过/失败
            passed = all(validation.values()) if validation else True

            # 保存 artifacts
            case_dir = os.path.join(self.output_dir, config.id)
            os.makedirs(case_dir, exist_ok=True)

            # 保存 timeline (WorldState snapshots)
            timeline_path = os.path.join(case_dir, "timeline.json")
            timeline = [s.to_dict() for s in runner.snapshots]
            with open(timeline_path, "w") as f:
                json.dump(timeline, f, indent=2, default=str)

            # 保存结果摘要
            result_path = os.path.join(case_dir, "result.json")
            with open(result_path, "w") as f:
                json.dump({
                    "case_id": config.id,
                    "name": config.name,
                    "seed": config.seed,
                    "passed": passed,
                    "metrics": results,
                    "validation": validation,
                }, f, indent=2, default=str)

            duration = time.time() - start_time

            return BenchmarkResult(
                case_id=config.id,
                name=config.name,
                category=self._get_category(yaml_path),
                seed=config.seed or 42,
                passed=passed,
                metrics=results,
                validation=validation,
                artifacts={
                    "timeline": timeline_path,
                    "result": result_path,
                },
                duration_sec=round(duration, 2),
            )

        except Exception as e:
            duration = time.time() - start_time
            case_id = os.path.basename(yaml_path).replace(".yaml", "").split("_")[0]
            return BenchmarkResult(
                case_id=case_id,
                name=yaml_path,
                category=self._get_category(yaml_path),
                seed=42,
                passed=False,
                metrics={},
                validation={},
                artifacts={},
                duration_sec=round(duration, 2),
                error=str(e),
            )

    def run_batch(self, yaml_dir: str, pattern: str = "*.yaml") -> BenchmarkReport:
        """批量运行所有 benchmark"""
        yaml_files = sorted(glob.glob(os.path.join(yaml_dir, "**", pattern), recursive=True))

        report = BenchmarkReport(timestamp=time.strftime("%Y-%m-%d %H:%M:%S"))

        for yaml_path in yaml_files:
            result = self.run_single(yaml_path)
            report.results.append(result.to_dict())
            report.total += 1

            cat = result.category
            if cat not in report.by_category:
                report.by_category[cat] = {"total": 0, "passed": 0, "failed": 0, "errored": 0}
            report.by_category[cat]["total"] += 1

            if result.error is not None:
                report.errored += 1
                report.by_category[cat]["errored"] += 1
            elif result.passed:
                report.passed += 1
                report.by_category[cat]["passed"] += 1
            else:
                report.failed += 1
                report.by_category[cat]["failed"] += 1

        report.pass_rate = (report.passed / report.total * 100) if report.total > 0 else 0.0

        # 保存报告
        report_path = os.path.join(self.output_dir, "bench_report.json")
        with open(report_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2, default=str)

        return report

    def _get_category(self, yaml_path: str) -> str:
        """从路径提取类别"""
        parts = yaml_path.split(os.sep)
        for p in parts:
            if p.startswith(("A_", "B_", "C_", "D_", "E_", "F_")):
                return p
        return "unknown"


def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description="Run ReflexMarket-Bench")
    parser.add_argument("--dir", default="scenarios/bench", help="Benchmark YAML directory")
    parser.add_argument("--output", default="outputs/bench", help="Output directory")
    args = parser.parse_args()

    runner = BenchmarkRunner(output_dir=args.output)
    report = runner.run_batch(args.dir)

    print(report.summary_str())

    # 保存文本报告
    report_txt_path = os.path.join(args.output, "bench_report.txt")
    with open(report_txt_path, "w") as f:
        f.write(report.summary_str())
    print(f"\nReport saved to: {args.output}/bench_report.json")
    print(f"Report saved to: {report_txt_path}")


if __name__ == "__main__":
    main()
