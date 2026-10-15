"""파이프라인 결과와 리포트 생성 로직 검증.

실행: python -m unittest discover -s tests -v
입력 경로는 환경변수 F1_INPUT(기본 data/01_raw/F1_distribution.zip)로 바꿀 수 있다.
"""
import hashlib, os, sys, tempfile, unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline import recovery as rp  # noqa: E402

INPUT = Path(os.environ.get("F1_INPUT", ROOT / "data" / "01_raw" / "F1_distribution.zip"))


def source_hashes():
    """원본(zip 파일 또는 폴더의 CSV)의 해시 — 실행 전후 원본이 그대로인지 확인용."""
    files = [INPUT] if INPUT.is_file() else sorted((INPUT / "all_years").glob("*.csv"))
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def read(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


@unittest.skipUnless(INPUT.is_file() or (INPUT / "all_years" / "laps.csv").exists() or (INPUT / "laps.csv").exists(), "입력 데이터 없음")
class PipelineReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "run1"
        cls.before = source_hashes()
        cls.info = rp.run(INPUT, cls.out)
        reports = cls.out / "reports"
        cls.issues = read(reports / "validation_issues.csv")
        cls.repairs = read(reports / "repair_detail.csv")
        cls.dq = pd.read_csv(reports / "dq_summary.csv")
        cls.files = pd.read_csv(reports / "repair_summary.csv")
        cls.repaired = {name: read(cls.out / "repaired" / name) for name in rp.FILES}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_source_files_untouched(self):
        after = source_hashes()
        self.assertEqual(self.before, after)

    def test_every_issue_has_known_code_and_type(self):
        catalogue = rp.load_catalogue()
        self.assertTrue(set(self.issues["diagnostic_code"]) <= set(catalogue))
        for col in ["error_type", "severity", "action", "status"]:
            self.assertFalse((self.issues[col] == "").any(), col)
        self.assertTrue(self.issues["issue_id"].is_unique)

    def test_summary_counts_add_up(self):
        self.assertTrue((self.dq["detected"] == self.dq["repaired"] + self.dq["accepted"] + self.dq["open"]).all())
        self.assertEqual(int(self.dq["detected"].sum()), len(self.issues))
        self.assertEqual(int(self.files["issue_count"].sum()), len(self.issues))

    def test_residual_equals_unrepaired(self):
        # 복구 후 같은 규칙으로 다시 검사하면 복구된 건은 사라지고 허용·미해결만 남아야 한다
        self.assertTrue((self.dq["residual_after_repair"] == self.dq["accepted"] + self.dq["open"]).all(),
                        self.dq[self.dq["residual_after_repair"] != self.dq["accepted"] + self.dq["open"]].to_string())

    def test_repair_detail_matches_issues_and_output(self):
        repaired_ids = set(self.issues.loc[self.issues["status"] == "REPAIRED", "issue_id"])
        self.assertEqual(repaired_ids, set(self.repairs["issue_id"]))
        indexed = {name: df.set_index(df[rp.KEYS[name]].astype(str).agg("|".join, axis=1)) for name, df in self.repaired.items()}
        for row in self.repairs.itertuples(index=False):
            hit = indexed[row.file].loc[[row.row_key]]
            self.assertEqual(len(hit), 1, row.issue_id)
            self.assertEqual(hit.iloc[0][row.field], row.new_value, row.issue_id)
            self.assertEqual(hit.iloc[0]["original_" + row.field], row.old_value, row.issue_id)

    def test_unchanged_rows_keep_original_values(self):
        for name, df in self.repaired.items():
            same = df[df["repair_status"] == "UNCHANGED"]
            for col in rp.SCHEMA[name]:
                self.assertTrue((same[col] == same["original_" + col]).all(), f"{name}.{col}")

    def test_quarantine_files_match_flags(self):
        for name, df in self.repaired.items():
            quarantine = read(self.out / "quarantine" / name)
            self.assertEqual(len(quarantine), int((df["quarantine_flag"] == "Y").sum()), name)

    def test_known_contamination_repaired(self):
        sessions = self.repaired["sessions.csv"].set_index("session_key")
        self.assertEqual(sessions.at["9126", "meeting_key"], "1214")
        self.assertEqual(sessions.at["9157", "meeting_key"], "1218")
        drivers = self.repaired["drivers.csv"].set_index(["session_key", "driver_number"])
        self.assertEqual(drivers.at[("9523", "1"), "full_name"], "Max VERSTAPPEN")
        self.assertEqual(drivers.at[("9523", "16"), "full_name"], "Charles LECLERC")
        self.assertEqual(drivers.at[("9523", "18"), "team_name"], "Aston Martin")
        self.assertEqual(drivers.at[("9606", "63"), "team_name"], "Mercedes")
        verstappen = self.repaired["drivers.csv"].query("full_name == 'Max VERSTAPPEN'")["country_code"]
        self.assertEqual(set(verstappen) - {""}, {"NED"})

    def test_no_statistical_imputation(self):
        # 기획서 4.2: 결측은 임의 보정하지 않는다 → 속도 결측은 그대로 남아야 한다
        laps = self.repaired["laps.csv"]
        self.assertTrue(((laps["original_i1_speed"] == "") == (laps["i1_speed"] == "")).all())

    def test_rerun_is_identical(self):
        out2 = Path(self.tmp.name) / "run2"
        rp.run(INPUT, out2)
        for sub in ["repaired", "reports"]:
            for path in (self.out / sub).glob("*.csv"):
                self.assertEqual(path.read_bytes(), (out2 / sub / path.name).read_bytes(), path.name)


if __name__ == "__main__":
    unittest.main()
