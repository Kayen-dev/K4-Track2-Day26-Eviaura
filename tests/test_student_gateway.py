"""Checks the student gateway's local admission and rewrite decisions."""

from agent.gateway import Command, Gateway
from agent.telemetry import RecordingGatewayContext


def _gateway(*, scopes=frozenset({"wiki.read"}), leases=()):
    ctx = RecordingGatewayContext(
        act="learner:sv-0417", sub="agent:test", scopes=scopes,
        credits=100, round=1, call_index=0, leases=leases,
    )
    return Gateway(ctx)


def _command(server, tool, *, args=None, headers=None, fields=(), lease_id=None):
    return Command(
        cmd_id="cmd:0000", kind="mcp", raw=f"MCP {server}.{tool}",
        server=server, tool=tool, args=args or {}, fields=fields,
        headers=headers or {}, lease_id=lease_id, call_index=0,
    )


def test_get_frame_requires_current_lease():
    cmd = _command("slides", "get_frame", args={"anchor": "Frame:x/w/001"}, lease_id="lse_old")
    assert _gateway(leases=("lse_new",)).decide(cmd).verdict == "deny"
    assert _gateway(leases=("lse_old",)).decide(cmd).verdict == "forward"


def test_record_mastery_requires_owner_scope_and_write_headers():
    headers = {"if-match": "sha256:abc", "idempotency-key": "idem-1"}
    own = _command("progress", "record_mastery", args={"learner": "Learner:sv-0417"}, headers=headers)
    other = _command("progress", "record_mastery", args={"learner": "Learner:sv-0392"}, headers=headers)
    scopes = frozenset({"wiki.read", "wiki.write:progress"})
    assert _gateway().decide(own).verdict == "deny"
    assert _gateway(scopes=scopes).decide(other).verdict == "deny"
    assert _gateway(scopes=scopes).decide(_command("progress", "record_mastery", args=own.args)).verdict == "deny"
    assert _gateway(scopes=scopes).decide(own).verdict == "forward"


def test_catalog_dump_is_narrowed_without_mutating_command():
    cmd = _command("registry", "list_servers", fields=("*",))
    decision = _gateway().decide(cmd)
    assert decision.verdict == "rewrite"
    assert decision.call.fields == ("name",)
    assert cmd.fields == ("*",)


def test_normal_read_passes_through():
    cmd = _command("slides", "query", args={"q": "MCP"}, fields=("body", "title"))
    decision = _gateway().decide(cmd)
    assert decision.verdict == "forward"
    assert decision.call.fields == cmd.fields


def test_a2a_requires_verified_card_skill_audience_and_act():
    gw = _gateway()
    cmd = _command("curriculum-analyst", "which_days_cover", args={"learner": "learner:sv-0417"},
                   headers={"aud": "curriculum-analyst"})
    assert gw.decide(cmd).verdict == "forward"
    gw.note_card("curriculum-analyst", {"verified": False, "skills": ["which_days_cover"]})
    assert gw.decide(cmd).verdict == "deny"
    gw.note_card("curriculum-analyst", {"verified": True, "skills": ["which_days_cover"]})
    wrong_audience = _command("curriculum-analyst", "which_days_cover", args=cmd.args,
                              headers={"aud": "roster"})
    assert gw.decide(wrong_audience).verdict == "deny"
    wrong_learner = _command("curriculum-analyst", "which_days_cover",
                             args={"learner": "learner:sv-0392"}, headers=cmd.headers)
    assert gw.decide(wrong_learner).verdict == "deny"


def test_rejects_body_route_and_reused_write_key():
    assert _gateway().decide(_command("slides", "query", args={"q": "mcp", "route": "c"})).verdict == "deny"
    gw = _gateway(scopes=frozenset({"wiki.read", "wiki.write:progress"}))
    cmd = _command("progress", "record_mastery", args={"learner": "learner:sv-0417"},
                   headers={"if-match": "sha256:abc", "idempotency-key": "idem-1"})
    assert gw.decide(cmd).verdict == "forward"
    assert gw.decide(cmd).verdict == "deny"
