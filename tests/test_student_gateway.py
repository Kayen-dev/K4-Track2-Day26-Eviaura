"""Checks the student gateway's local admission and rewrite decisions."""

from agent.gateway import Command, Gateway
from agent.telemetry import RecordingGatewayContext
from kit.loop.agent import canonicalise_action


def _gateway(*, scopes=frozenset({"wiki.read"}), leases=(), credits=100):
    ctx = RecordingGatewayContext(
        act="learner:sv-0417", sub="agent:test", scopes=scopes,
        credits=credits, round=1, call_index=0, leases=leases,
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
    decision = _gateway(leases=("lse_old",)).decide(cmd)
    assert decision.verdict == "rewrite"
    assert decision.call.args["anchor"] == "Frame:x/w/001"
    assert decision.call.headers["mcp-replica"] == "w"


def test_record_mastery_requires_owner_scope_and_write_headers():
    headers = {"if-match": "sha256:abc", "idempotency-key": "idem-1"}
    own = _command("progress", "record_mastery", args={"learner": "learner:sv-0417"}, headers=headers)
    other = _command("progress", "record_mastery", args={"learner": "learner:sv-0392"}, headers=headers)
    scopes = frozenset({"wiki.read", "wiki.write:progress"})
    assert _gateway().decide(own).verdict == "deny"
    assert _gateway(scopes=scopes).decide(other).verdict == "deny"
    assert _gateway(scopes=scopes).decide(_command("progress", "record_mastery", args=own.args)).verdict == "deny"
    assert _gateway(scopes=scopes).decide(own).verdict == "deny"  # no trusted provenance
    trusted = _gateway(scopes=scopes)
    trusted.note_provenance("Learner:sv-0417", "sha256:abc")
    assert trusted.decide(own).verdict == "forward"
    mismatch = _command(
        "progress", "record_mastery",
        args={"learner": "learner:sv-0417", "anchor": "Learner:sv-0392"},
        headers={"if-match": "sha256:abc", "idempotency-key": "idem-2"},
    )
    assert trusted.decide(mismatch).verdict == "deny"


def test_record_mastery_accepts_the_trusted_anchor_argument():
    gw = _gateway(scopes=frozenset({"wiki.read", "wiki.write:progress"}))
    gw.note_provenance("Learner:sv-0417", "sha256:abc")
    cmd = _command(
        "progress", "record_mastery", args={"anchor": "Learner:sv-0417"},
        headers={"if-match": "sha256:abc", "idempotency-key": "idem-1"},
    )
    assert gw.decide(cmd).verdict == "forward"


def test_catalog_dump_is_narrowed_without_mutating_command():
    cmd = _command("registry", "list_servers", fields=("*",))
    decision = _gateway().decide(cmd)
    assert decision.verdict == "rewrite"
    assert decision.call.fields == ("name",)
    assert cmd.fields == ("*",)


def test_other_wildcard_masks_use_the_tool_default():
    cmd = _command("slides", "get_frame", fields=("*",), lease_id="lse_live")
    decision = _gateway(leases=("lse_live",)).decide(cmd)
    assert decision.verdict == "rewrite"
    assert decision.call.fields == ("body", "title")


def test_query_does_not_claim_a_single_replica():
    cmd = _command("slides", "query", args={"q": "MCP"}, fields=("body", "title"))
    decision = _gateway().decide(cmd)
    assert decision.verdict == "forward"
    assert decision.call.fields == cmd.fields
    assert "mcp-replica" not in decision.call.headers


def test_reads_require_wiki_read_scope():
    cmd = _command("slides", "query", args={"q": "MCP"})
    assert _gateway(scopes=frozenset()).decide(cmd).verdict == "deny"


def test_query_strips_unsupported_replica_header():
    action = canonicalise_action(
        "MCP slides.query q=MCP fields=title limit=1 header.mcp-replica=c",
        call_index=0,
    )
    cmd = Command.from_action_dict(action, cmd_id="cmd:0000")
    decision = _gateway().decide(cmd)
    assert decision.verdict == "rewrite"
    assert decision.call.fields == ("title",)
    assert decision.call.args["limit"] == 1
    assert "mcp-replica" not in decision.call.headers


def test_replica_header_rejects_unknown_values():
    invalid = _command("slides", "query", args={"q": "MCP"}, headers={"mcp-replica": "latest"})
    assert _gateway().decide(invalid).verdict == "deny"


def test_replica_choice_uses_trusted_provenance_drift():
    gw = _gateway(leases=("lse_live",))
    gw.note_provenance("Frame:day09/w/001", "etag-working")
    gw.note_provenance("Frame:day09/c/001", "etag-canonical")
    cmd = _command(
        "slides", "get_frame", args={"anchor": "Frame:day09/w/001"},
        headers={"mcp-replica": "w"}, lease_id="lse_live",
    )
    decision = gw.decide(cmd)
    assert decision.verdict == "rewrite"
    assert decision.call.headers["mcp-replica"] == "c"
    assert decision.call.args["anchor"] == "Frame:day09/c/001"


def test_get_frame_uses_working_for_paired_equal_provenance():
    gw = _gateway(leases=("lse_live",))
    gw.note_provenance("Frame:day09/w/001", "same-etag")
    gw.note_provenance("Frame:day09/c/001", "same-etag")
    cmd = _command(
        "slides", "get_frame", args={"anchor": "Frame:day09/c/001"},
        headers={"mcp-replica": "c"}, lease_id="lse_live",
    )
    decision = gw.decide(cmd)
    assert decision.verdict == "rewrite"
    assert decision.call.args["anchor"] == "Frame:day09/w/001"
    assert decision.call.headers["mcp-replica"] == "w"


def test_get_frame_preserves_unpaired_requested_replica_on_a_drifting_path():
    gw = _gateway(leases=("lse_live",))
    gw.note_provenance("Frame:day09/w/001", "etag-working")
    gw.note_provenance("Frame:day09/c/001", "etag-canonical")
    cmd = _command(
        "slides", "get_frame", args={"anchor": "Frame:day09/w/002"},
        headers={"mcp-replica": "w"}, lease_id="lse_live",
    )

    decision = gw.decide(cmd)

    assert decision.verdict == "forward"
    assert decision.call.args["anchor"] == "Frame:day09/w/002"
    assert decision.call.headers["mcp-replica"] == "w"


def test_get_frame_routes_replica_anchor_without_frame_index():
    gw = _gateway(leases=("lse_live",))
    gw.note_provenance("Deck:day09/w", "etag-working")
    gw.note_provenance("Deck:day09/c", "etag-canonical")
    cmd = _command(
        "slides", "get_frame", args={"anchor": "Deck:day09/w"},
        headers={"mcp-replica": "w"}, lease_id="lse_live",
    )
    decision = gw.decide(cmd)
    assert decision.verdict == "rewrite"
    assert decision.call.args["anchor"] == "Deck:day09/c"
    assert decision.call.headers["mcp-replica"] == "c"


def test_deprecated_search_rewrites_to_its_successor():
    cmd = _command("slides", "search", args={"q": "MCP"}, headers={"mcp-replica": "c"})
    decision = _gateway().decide(cmd)
    assert decision.verdict == "rewrite"
    assert (decision.call.server, decision.call.tool) == ("slides", "query")
    assert "mcp-replica" not in decision.call.headers


def test_query_limit_fits_the_round_and_shared_credit_budgets():
    gw = _gateway(leases=("lse_live",))
    query = _command("slides", "query", args={"q": "MCP", "limit": "50"}, fields=("title", "body"))
    first = gw.decide(query)
    assert first.verdict == "rewrite"
    assert first.call.args["limit"] == 8  # 3 mask credits + at most 8 row credits = 11

    gw.ctx.credits = 89  # the capped query costs 11 credits
    frame = _command("slides", "get_frame", args={"anchor": "Frame:x/w/001"}, lease_id="lse_live")
    assert gw.decide(frame).verdict == "deny"  # the query already spent the 11-credit allowance

    gw.ctx.round = 2
    assert gw.decide(frame).verdict == "rewrite"
    assert _gateway(credits=3).decide(_command("slides", "query", args={"q": "MCP"}, fields=("body",))).verdict == "deny"


def test_write_rejects_if_match_older_than_trusted_provenance():
    scopes = frozenset({"wiki.read", "wiki.write:progress"})
    gw = _gateway(scopes=scopes)
    gw.note_provenance("Learner:sv-0417", "sha256:current")
    stale = _command(
        "progress", "record_mastery", args={"learner": "Learner:sv-0417"},
        headers={"if-match": "sha256:old", "idempotency-key": "idem-old"},
    )
    assert gw.decide(stale).verdict == "deny"
    fresh = _command(
        "progress", "record_mastery", args={"learner": "Learner:sv-0417"},
        headers={"if-match": "sha256:current", "idempotency-key": "idem-current"},
    )
    assert gw.decide(fresh).verdict == "forward"


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
    learner = "learner:sv-0417"
    gw.note_provenance("Learner:sv-0417", "sha256:abc")
    cmd = _command("progress", "record_mastery", args={"learner": learner},
                   headers={"if-match": "sha256:abc", "idempotency-key": "idem-1"})
    assert gw.decide(cmd).verdict == "forward"
    assert gw.decide(cmd).verdict == "deny"
