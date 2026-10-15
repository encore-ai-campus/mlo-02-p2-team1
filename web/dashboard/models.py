"""Gold 데이터 마트 (build_gold 명령이 채우고, 화면은 읽기만 한다).

기획서 6장 Gold 9개 중 Decision Board 화면에 필요한 것만 우선 만든다.
- GoldDriverProfile  ≈ gold_driver_profile (시즌 × 드라이버)
- GoldTeamProfile    ≈ gold_team_profile + gold_team_pit_benchmark (시즌 × 팀)
- GoldSnapshot       화면 한 장에 필요한 값 묶음(JSON) — 실행 시점·출처와 함께 보관
"""
from django.db import models


class GoldDriverProfile(models.Model):
    season = models.SmallIntegerField()
    full_name = models.CharField(max_length=64)
    acronym = models.CharField(max_length=8)
    team_name = models.CharField(max_length=64)
    races = models.SmallIntegerField()
    clean_laps = models.IntegerField()
    pace_pct = models.FloatField(help_text="경기 내 필드 중앙값 대비 %, 낮을수록 빠름")
    pace_top_pct = models.FloatField(null=True)
    teammate_gap_s = models.FloatField(null=True, help_text="팀 동료 대비 초/랩, 음수면 더 빠름")
    teammate_top_pct = models.FloatField(null=True)
    consistency_iqr_s = models.FloatField(null=True)
    consistency_top_pct = models.FloatField(null=True)
    tyre_ms_per_lap = models.FloatField(null=True)
    tyre_top_pct = models.FloatField(null=True)
    race_base_points = models.IntegerField()
    points_top_pct = models.FloatField(null=True)
    avg_positions_gained = models.FloatField(null=True)
    dnf = models.SmallIntegerField()
    starts = models.SmallIntegerField()

    class Meta:
        db_table = "gold_driver_profile"
        unique_together = [("season", "full_name")]


class GoldTeamProfile(models.Model):
    season = models.SmallIntegerField()
    team_name = models.CharField(max_length=64)
    pace_pct = models.FloatField(null=True)
    tyre_ms_per_lap = models.FloatField(null=True)
    stint_median_laps = models.FloatField(null=True)
    stops_per_race = models.FloatField(null=True)
    race_base_points = models.IntegerField()
    points_rank = models.SmallIntegerField()
    pit_positions_lost = models.FloatField(null=True)
    pit_time_lost_s = models.FloatField(null=True)
    lane_loss_median_s = models.FloatField(null=True)
    slow_stop_pct = models.FloatField(null=True)
    stop_median_s = models.FloatField(null=True)
    stop_over4_pct = models.FloatField(null=True)

    class Meta:
        db_table = "gold_team_profile"
        unique_together = [("season", "team_name")]


class GoldSnapshot(models.Model):
    built_at = models.DateTimeField(auto_now_add=True)
    season = models.SmallIntegerField()
    target_team = models.CharField(max_length=64)
    source = models.CharField(max_length=255)
    payload = models.JSONField()

    class Meta:
        db_table = "gold_snapshot"
        ordering = ["-built_at"]
