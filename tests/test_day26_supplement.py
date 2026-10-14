"""Additional runtime evidence; existing student code/tests stay untouched."""
from dataclasses import replace
import time

import pytest

from agent.gateway import Command, Gateway
from agent.telemetry import RecordingGatewayContext
from kit.mcp.servers import handle
from kit.world.fixture import build_fixture_world
from kit.world.loader import World
from eval.prosecute import load_fixtures, prosecute, _schema_errors, family_of


def command(index, *, tool="query", args=None, fields=("title",), lease=None):
    return Command(cmd_id=f"cmd:{index:04d}", kind="mcp", raw="MCP slides.query",
                   server="slides", tool=tool, args=args or {"q": "field mask", "limit": 1},
                   fields=fields, headers={}, lease_id=lease, call_index=index)


def context():
    return RecordingGatewayContext(act="learner:sv-0417", sub="agent:test",
                                   scopes=frozenset({"wiki.read"}), credits=100,
                                   round=1, call_index=0)


def test_one_gateway_uses_authoritative_credits_for_ten_rounds(tmp_path):
    """Unlike spar's per-exchange contexts, keep one gateway and real costs."""
    world = World.load(build_fixture_world(tmp_path / "world", include_truth=False))
    ctx = context()
    gateway = Gateway(ctx)
    returned = []
    for round_no in range(1, 11):
        ctx.round = round_no
        query = command(2 * round_no)
        decision = gateway.decide(query)
        assert decision.verdict == "forward"
        result = handle(world, decision.call)
        assert result["ok"] and result["anchors"] and result["lease_id"]
        ctx.credits -= result["cost"]
        ctx.leases = (result["lease_id"],)
        frame = command(2 * round_no + 1, tool="get_frame", args={"anchor": result["anchors"][0]},
                        fields=("body",), lease=result["lease_id"])
        decision = gateway.decide(frame)
        assert decision.verdict == "forward"
        read = handle(world, decision.call)
        assert read["ok"] and read["rows"]
        ctx.credits -= read["cost"]
        assert ctx.credits >= 0
        returned.append(read["anchors"])
        ctx.leases = ()
        assert gateway.decide(frame).verdict == "deny"
    assert len(returned) == 10
    ctx.credits = 0
    assert gateway.decide(command(99)).verdict == "deny"


@pytest.mark.parametrize("change", [
    {"headers": {"x-server-fingerprint": "unvouched"}},
    {"headers": {"x-card-signature": "invalid"}},
    {"server": "unknown-server"},
    {"args": {"q": "MCP", "learner": "learner:sv-0392"}},
])
def test_rejected_commands_remain_free_and_leave_original_unchanged(change):
    ctx = context()
    gateway = Gateway(ctx)
    cmd = replace(command(1), **change)
    before = cmd.to_dict()
    result = gateway.decide(cmd)
    assert result.verdict == "deny" and result.call is None and result.reason
    assert ctx.credits == 100 and cmd.to_dict() == before


def test_prosecutor_schema_and_deadline_on_every_fixture():
    maximum = 0.0
    for fixture in load_fixtures():
        start = time.perf_counter()
        claims = prosecute(fixture["trace"], fixture["answer"], fixture["card"])["claims"]
        maximum = max(maximum, time.perf_counter() - start)
        assert len(claims) <= 4
        assert len({family_of(c["cls"]) for c in claims}) == len(claims)
        assert all(not _schema_errors(c) for c in claims)
    assert maximum < 5


def test_gateway_deadline_over_a_sustained_duel():
    ctx = context()
    gateway = Gateway(ctx)
    maximum = 0.0
    for round_no in range(1, 11):
        ctx.round = round_no
        for index in range(4):
            start = time.perf_counter()
            decision = gateway.decide(command(round_no * 4 + index))
            maximum = max(maximum, time.perf_counter() - start)
            assert decision.verdict in ("forward", "rewrite", "deny")
    assert maximum < 0.25
