import math

import pytest

from coldroom import simulation as simmod
from coldroom.simulation import Simulation
from conftest import FakeClock


def run(sim, clock, seconds, step=1.0):
    snap = None
    for _ in range(int(seconds / step)):
        clock.advance(step)
        snap = sim.snapshot()
    return snap


@pytest.fixture
def pair():
    clock = FakeClock()
    return Simulation(clock=clock), clock


def test_starts_at_minus_18_with_matching_setpoint(pair):
    sim, _ = pair
    s = sim.snapshot()
    assert s["setpoint_c"] == -18.0
    assert s["measured_c"] == -18.0
    assert s["alarm"]["active"] is False


def test_requested_and_measured_are_separate_values(pair):
    sim, clock = pair
    sim.set_setpoint(-10)
    s = run(sim, clock, 1)
    assert s["setpoint_c"] == -10.0
    assert s["measured_c"] != s["setpoint_c"]


def test_temperature_changes_gradually_not_instantly(pair):
    sim, clock = pair
    sim.set_setpoint(-10)
    after_10 = run(sim, clock, 10)["measured_c"]
    assert -18.0 < after_10 < -16.0
    after_60 = run(sim, clock, 50)["measured_c"]
    assert after_10 < after_60 < -10.0


def test_measured_converges_toward_setpoint(pair):
    sim, clock = pair
    sim.set_setpoint(-10)
    s = run(sim, clock, 200)
    assert -11.0 < s["measured_c"] < -9.0


def test_cooling_toward_a_colder_setpoint(pair):
    sim, clock = pair
    sim.set_setpoint(-30)
    s = run(sim, clock, 100)
    assert s["measured_c"] < -28.0
    assert s["phase"] in {"cooling", "holding"}


@pytest.mark.parametrize("bad", [10.01, -40.01, 100, -100, math.nan, math.inf, -math.inf])
def test_setpoint_is_bounded_to_global_range(pair, bad):
    sim, _ = pair
    with pytest.raises(ValueError):
        sim.set_setpoint(bad)
    assert sim.snapshot()["setpoint_c"] == -18.0


@pytest.mark.parametrize("bad", [True, "5", None, [1]])
def test_setpoint_rejects_non_numbers(pair, bad):
    sim, _ = pair
    with pytest.raises(TypeError):
        sim.set_setpoint(bad)


def test_global_range_edges_are_allowed(pair):
    sim, _ = pair
    assert sim.set_setpoint(10) == 10.0
    assert sim.set_setpoint(-40) == -40.0


def test_warm_setpoint_raises_high_alarm_after_a_delay(pair):
    sim, clock = pair
    sim.set_setpoint(-10)
    early = run(sim, clock, 20)
    assert early["alarm"]["active"] is False
    late = run(sim, clock, 60)
    assert late["alarm"]["active"] is True
    assert late["alarm"]["kind"] == "high"


def test_alarm_pending_between_crossing_and_delay(pair):
    sim, clock = pair
    sim.set_setpoint(0)
    seen_pending = False
    for _ in range(120):
        clock.advance(1)
        a = sim.snapshot()["alarm"]
        seen_pending = seen_pending or a["pending"]
    assert seen_pending


def test_cold_setpoint_raises_low_alarm(pair):
    sim, clock = pair
    sim.set_setpoint(-40)
    s = run(sim, clock, 150)
    assert s["alarm"]["active"] is True
    assert s["alarm"]["kind"] == "low"


def test_alarm_clears_when_back_in_range(pair):
    sim, clock = pair
    sim.set_setpoint(0)
    assert run(sim, clock, 120)["alarm"]["active"] is True
    sim.set_setpoint(-18)
    s = run(sim, clock, 200)
    assert s["alarm"]["active"] is False


def test_defrost_cycle_happens_and_switches_compressor_off(pair):
    sim, clock = pair
    phases = []
    for _ in range(330):
        clock.advance(1)
        s = sim.snapshot()
        phases.append((s["phase"], s["compressor_on"]))
    defrost = [p for p in phases if p[0] == "defrost"]
    assert len(defrost) >= 10
    assert all(on is False for _, on in defrost)


def test_normal_operation_does_not_alarm_at_default_setpoint(pair):
    sim, clock = pair
    for _ in range(900):
        clock.advance(1)
        assert sim.snapshot()["alarm"]["active"] is False


def test_history_is_bounded(pair):
    sim, clock = pair
    s = run(sim, clock, 3600, step=5.0)
    assert 0 < len(s["history"]) <= simmod.HISTORY_MAX
    assert all(len(sample) == 3 for sample in s["history"])


def test_huge_clock_jump_is_capped_and_fast(pair):
    sim, clock = pair
    clock.advance(10**7)
    s = sim.snapshot()
    assert s["sim_time_s"] <= simmod.MAX_CATCHUP_S + 1


def test_clock_going_backwards_is_harmless(pair):
    sim, clock = pair
    run(sim, clock, 10)
    clock.advance(-50)
    assert sim.snapshot()["measured_c"] == pytest.approx(-18.0, abs=1.0)


def test_simulation_is_deterministic():
    results = []
    for _ in range(2):
        clock = FakeClock()
        sim = Simulation(clock=clock)
        sim.set_setpoint(-12)
        results.append(run(sim, clock, 100)["measured_c"])
    assert results[0] == results[1]
