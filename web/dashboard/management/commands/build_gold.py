import time

from django.core.management.base import BaseCommand
from django.db import transaction

from dashboard import gold
from dashboard.models import GoldDriverProfile, GoldSnapshot, GoldTeamProfile


class Command(BaseCommand):
    help = "MySQL 설계 스키마에서 Decision Board용 Gold 지표를 계산해 gold_* 테이블에 저장한다."

    def handle(self, *args, **opts):
        t0 = time.time()
        payload = gold.build(log=lambda m: self.stdout.write(f"  · {m}"))
        X, season = payload["enriched"], payload["season"]
        pl = X["pitLoss"]
        stop = {r["t"]: r["sm"] for r in payload["teams25"]}
        rank = {t: i + 1 for i, t in enumerate(X["teamPoints25"])}
        with transaction.atomic():
            GoldDriverProfile.objects.filter(season=season).delete()
            GoldDriverProfile.objects.bulk_create([GoldDriverProfile(
                season=season, full_name=r["n"], acronym=r["a"], team_name=r["t"], races=r["r"], clean_laps=r["l"],
                pace_pct=r["pace"], pace_top_pct=r["paceTop"], teammate_gap_s=r["tm"], teammate_top_pct=r["tmTop"],
                consistency_iqr_s=r["iqr"], consistency_top_pct=r["iqrTop"], tyre_ms_per_lap=r["tyre"], tyre_top_pct=r["tyreTop"],
                race_base_points=r["pts"], points_top_pct=r["ptsTop"], avg_positions_gained=r["gain"], dnf=r["dnf"], starts=r["starts"],
            ) for r in X["drivers25"]])
            GoldTeamProfile.objects.filter(season=season).delete()
            GoldTeamProfile.objects.bulk_create([GoldTeamProfile(
                season=season, team_name=t, pace_pct=v["pace"], tyre_ms_per_lap=v["tyre"], stint_median_laps=v["stint"],
                stops_per_race=v["stops"], race_base_points=v["pts"], points_rank=rank.get(t, 0),
                pit_positions_lost=pl["teams"].get(t, {}).get("lost"), pit_time_lost_s=pl["timeLoss"]["teams"].get(t),
                lane_loss_median_s=pl["pitGreen"].get(t, {}).get("lane_rel_med"), slow_stop_pct=pl["pitGreen"].get(t, {}).get("slow_pct"),
                stop_median_s=stop.get(t), stop_over4_pct=payload["stopOver4"].get(t),
            ) for t, v in X["teams25"].items()])
            GoldSnapshot.objects.create(season=season, target_team=payload["team"], payload=payload,
                                        source="MySQL f1_db (sql/04·05 설계 스키마) · 정제 v0.2.0 + 추가 데이터 5종")
        self.stdout.write(self.style.SUCCESS(
            f"Gold 저장 완료: 드라이버 {len(X['drivers25'])}명 · 팀 {len(X['teams25'])}개 · 스냅샷 1건 ({time.time() - t0:.0f}초)"))
