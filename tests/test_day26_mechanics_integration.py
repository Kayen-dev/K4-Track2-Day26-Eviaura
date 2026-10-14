"""Student gateway + real kit handlers, using a student fixture without truth.

Passing a reproduction of a gap is not a claim that the agent defended it.
JUnit properties retain the calls, decisions, charged results and conclusion.
"""
import json

import pytest

from agent.gateway import Command, Gateway
from agent.telemetry import RecordingGatewayContext
from kit.mcp.hardmode import HardMode, OPAQUE_DENOMINATOR, _seeded_int
from kit.mcp.mutations import MutableStack
from kit.mcp.servers import handle
from kit.mcp.specs import cost_of
from kit.mcp.types import ToolCall
from kit.world.fixture import FIXTURE_ANCHORS, FIXTURE_PATH_IDS, build_fixture_world
from kit.world.loader import World


class Session:
    """Test envelope: publish live leases/credits, execute, retain observations."""

    def __init__(self, world, *, hardmode=True, opaque=False):
        self.world = world
        self.ctx = RecordingGatewayContext(
            act="learner:sv-0417", sub="agent:vlearn-tutor", credits=100,
            scopes=frozenset({"wiki.read", "wiki.write:progress"}), round=1, call_index=0)
        self.gateway = Gateway(self.ctx)
        self.hm = HardMode(world=world, opaque_enabled=opaque,
                           degraded_replica_enabled=False) if hardmode else None
        if self.hm:
            self.hm.reset("day26-integration", world_id=world.manifest["world_id"])
        self.trace = []
        self.leases = {}
        self.index = 0
        self.stack = None

    def begin_round(self, number):
        self.ctx.round = number
        self.leases.clear()
        if self.hm:
            self.hm.begin_round(number)

    def send(self, server, tool, *, args=None, fields=(), headers=None, lease=None, index=None):
        index = self.index if index is None else index
        self.index = index + 1
        self.ctx.call_index = index
        self.ctx.leases = tuple(key for key, minted in self.leases.items() if 0 < index - minted <= 3)
        peer = server in {"curriculum-analyst", "citation-checker", "roster"}
        hdr = dict(headers or {})
        if peer:
            hdr.setdefault("aud", server)
        cmd = Command(cmd_id=f"cmd:{len(self.trace):04d}", kind="a2a" if peer else "mcp",
                      raw=f"{server}.{tool}", server=server, tool=tool, args=dict(args or {}),
                      fields=fields, headers=hdr, lease_id=lease, call_index=index)
        decision = self.gateway.decide(cmd)
        mutation = None
        if decision.verdict == "deny":
            result = {"ok": False, "cost": 0, "error": {"code": "gateway_denied"}}
        elif self.stack:
            result, mutation = self.stack.execute(decision.call)
        else:
            result = handle(self.world, decision.call, hardmode=self.hm)
        self.ctx.credits -= result["cost"]
        if result.get("ok") and (server, tool) == ("registry", "provenance"):
            self.gateway.note_provenance(cmd.args["anchor"], result["etag"])
        if result.get("ok") and result.get("lease_id"):
            self.leases[result["lease_id"]] = index
        self.trace.append({"command": cmd.to_dict(), "decision": decision.to_dict(),
                           "result": result, "mutation": mutation, "credits": self.ctx.credits})
        return result

    def evidence(self, record_property, conclusion):
        record_property("conclusion", conclusion)
        record_property("trace", json.dumps(self.trace, ensure_ascii=False))


@pytest.fixture
def session(tmp_path):
    world = World.load(build_fixture_world(tmp_path / "student-world", include_truth=False))
    assert not world.has_truth
    return Session(world)


def test_dynamic_mask_and_row_cost(session, record_property):
    narrow = session.send("slides", "query", args={"q": "MCP", "limit": 1}, fields=("title",))
    wide = session.send("slides", "query", args={"q": "MCP", "limit": 2}, fields=("title", "body"))
    assert narrow["ok"] and wide["ok"]
    assert "body" not in narrow["rows"][0] and "body" in wide["rows"][0]
    assert wide["cost"] > narrow["cost"]
    for event in session.trace:
        call = ToolCall.from_dict(event["decision"]["call"])
        assert event["result"]["cost"] == cost_of(call, len(event["result"]["rows"]))
    catalog = session.send("registry", "list_servers", fields=("*",))
    assert catalog["ok"] and session.trace[-1]["decision"]["verdict"] == "rewrite"
    assert set(catalog["rows"][0]) == {"name"}
    session.evidence(record_property, "Mask narrowing works; rows contribute to real server cost.")


def test_query_denied_when_one_row_cannot_be_funded(session, record_property):
    session.ctx.credits = 2
    result = session.send("slides", "query", args={"q": "MCP", "limit": 2}, fields=("title",))
    assert result["error"]["code"] == "gateway_denied" and result["cost"] == 0
    assert session.trace[-1]["decision"]["verdict"] == "deny"
    assert session.ctx.credits == 2
    session.evidence(record_property, "Gateway requires enough credit for one query row.")


@pytest.mark.parametrize("age", [3, 4])
def test_lease_window_at_gateway_and_server(session, record_property, age):
    query = session.send("slides", "query", args={"q": "MCP", "limit": 1}, index=0)
    lease = query["lease_id"]
    result = session.send("slides", "get_frame", args={"anchor": FIXTURE_ANCHORS["alpha_frame_w_001"]},
                          lease=lease, index=age)
    if age == 3:
        assert result["ok"]
    else:
        assert result["error"]["code"] == "gateway_denied" and result["cost"] == 0
        # Independently confirm the real server rejects the stale lease too.
        direct = handle(session.world, ToolCall("slides", "get_frame",
            {"anchor": FIXTURE_ANCHORS["alpha_frame_w_001"]}, lease_id=lease, call_index=age), hardmode=session.hm)
        assert direct["error"]["code"] == "lease_expired"
        record_property("direct_server_result", json.dumps(direct))
    session.evidence(record_property, "Lease boundary respected when the envelope publishes current leases.")


def test_lease_does_not_cross_rounds(session, record_property):
    query = session.send("slides", "query", args={"q": "MCP", "limit": 1})
    session.begin_round(2)
    result = session.send("slides", "get_frame", args={"anchor": FIXTURE_ANCHORS["alpha_frame_w_001"]},
                          lease=query["lease_id"])
    assert result["error"]["code"] == "gateway_denied" and result["cost"] == 0
    session.evidence(record_property, "Expired round lease denied without server charge.")


def test_write_requires_trusted_etag_and_single_use_key(session, record_property):
    args = {"anchor": "Learner:sv-0417", "learner": "Learner:sv-0417", "concept": "Concept:streamable-http"}
    provenance = session.send("registry", "provenance", args={"anchor": args["anchor"]})
    assert provenance["ok"]
    stale = {"if-match": "sha256:0000000000000000", "idempotency-key": "failed-write"}
    conflict = session.send("progress", "record_mastery", args=args, headers=stale)
    assert conflict["error"]["code"] == "gateway_denied" and conflict["cost"] == 0
    retry = session.send("progress", "record_mastery", args=args, headers=stale)
    assert retry["error"]["code"] == "gateway_denied" and retry["cost"] == 0
    fresh = session.send("registry", "provenance", args={"anchor": args["anchor"]})
    headers = {"if-match": fresh["etag"], "idempotency-key": "fresh-write"}
    success = session.send("progress", "record_mastery", args=args, headers=headers)
    assert success["ok"] and success["rows"][0]["receipt_id"]
    duplicate = session.send("progress", "record_mastery", args=args, headers=headers)
    assert duplicate["error"]["code"] == "gateway_denied" and duplicate["cost"] == 0
    session.evidence(record_property, "Gateway checks trusted etag and blocks a reused key; fresh write succeeds.")


def test_partial_native_cursor_can_be_consumed(session, record_property):
    session.hm = None  # Isolate the handler's native pagination from hard-mode wrapping.
    anchors, cursor = [], None
    direct_trace = []
    for index in range(30):
        args = {"q": "MCP", "ns": "Frame", "limit": 2}
        if cursor is not None:
            args["cursor"] = cursor
        call = ToolCall("slides", "query", args, fields=("title",), call_index=index)
        result = handle(session.world, call)
        direct_trace.append({"call": call.to_dict(), "result": result})
        assert result["ok"]
        anchors.extend(result["anchors"])
        if not result["partial"]:
            break
        assert result["continuation"]
        cursor = result["continuation"]
    else:
        pytest.fail("pagination did not terminate")
    expected = [p.anchor for p in session.world.search("MCP", ns="Frame", limit=100)]
    assert anchors == expected and len(anchors) == len(set(anchors))
    record_property("conclusion", "Native cursor returns all matching frames without duplicates.")
    record_property("trace", json.dumps(direct_trace, ensure_ascii=False))


def test_partial_hardmode_token_is_not_a_native_cursor(session, record_property):
    partial = session.send("slides", "query", args={"q": "MCP", "limit": 50}, fields=("title",))
    assert partial["ok"] and partial["partial"] and partial["continuation"].startswith("cont_")
    follow = session.send("slides", "query", args={"q": "MCP", "limit": 50, "cursor": partial["continuation"]})
    assert follow["error"]["code"] == "bad_request"
    session.evidence(record_property, "KIT LIMITATION: hard-mode continuation token cannot be used as native query cursor.")


def test_rate_limit_cross_round_charge_and_recovery(session, record_property):
    results = []
    for number in (1, 2, 3, 4):
        session.begin_round(number)
        results.append(session.send("citation-checker", "verify_source", args={"anchor": "Source:mcp-spec-2026-07-28"}))
    assert results[0]["ok"] and results[1]["ok"]
    assert results[2]["error"]["code"] == "rate_limited" and results[2]["cost"] > 0
    assert results[3]["ok"]
    session.evidence(record_property, "Server rate window enforces 2/3 rounds and charges denial; gateway does not preempt it.")


def test_opaque_unavailable_is_charged_and_replayable(session, record_property):
    session = Session(session.world, opaque=True)
    world_id = session.world.manifest["world_id"]
    index = next(i for i in range(200) if _seeded_int(world_id, "day26-integration", 1,
        "opaque", "glossary", "define", i, modulus=OPAQUE_DENOMINATOR) == 0)
    kwargs = {"args": {"term": "endpoint", "lang": "vi"}, "index": index}
    failed = session.send("glossary", "define", **kwargs)
    assert not failed["ok"] and failed["error"] == {"code": "unavailable"} and failed["cost"] > 0
    replay = Session(session.world, opaque=True).send("glossary", "define", **kwargs)
    assert replay == failed
    session.evidence(record_property, "Opaque failure is deterministic and charged; no model recovery is tested here.")


def test_wrong_language_silently_returns_a_different_sense(session, record_property):
    honest = session.send("glossary", "define", args={"term": "endpoint", "lang": "en"}, fields=("definition",))
    wrong = session.send("glossary", "define", args={"term": "endpoint", "lang": "fr"}, fields=("definition",))
    assert honest["ok"] and wrong["ok"]
    assert honest["anchors"] == [FIXTURE_ANCHORS["ambiguous_sense_en"]]
    assert wrong["anchors"] == [FIXTURE_ANCHORS["ambiguous_sense_vi"]]
    session.evidence(record_property, "GAP: gateway admits invalid lang; server silently selects another valid anchor.")


def test_deprecated_search_is_stamped_and_query_preserves_title_result(session, record_property):
    args = {"q": "MCP", "limit": 1}
    direct_old = handle(session.world, ToolCall("slides", "search", args, fields=("title",)))
    old = session.send("slides", "search", args=args, fields=("title",))
    new = session.send("slides", "query", args=args, fields=("title",))
    assert old["ok"] and new["ok"] and old["anchors"] == new["anchors"]
    assert direct_old["deprecated"] and direct_old["successor"] == "slides.query"
    assert not old["deprecated"] and not new["deprecated"]
    assert session.trace[-2]["decision"]["call"]["tool"] == "query"
    # Price varies with mask/rows; a one-row title search costs the same as query.
    assert old["cost"] == new["cost"]
    session.evidence(record_property, "Server stamps deprecated search; gateway upgrades it to query.")


@pytest.mark.parametrize("scope", ["content", "header"])
def test_replica_mutation_does_not_get_verified_by_gateway(session, record_property, scope):
    query = session.send("slides", "query", args={"q": "MCP", "limit": 1})
    path = FIXTURE_PATH_IDS["alpha"]
    session.stack = MutableStack(world=session.world, act=session.ctx.act, hardmode=session.hm)
    session.stack.arm({"id": "integration-replica", "kind": "attack",
        "class": "drift" if scope == "content" else "replica_flip",
        "mutation": {"target": "mcp:slides", "op": "swap_replica", "value": {"path_id": path, "scope": scope}},
        "trigger": {"on": "call_index", "gte": 1}})
    result = session.send("slides", "get_frame", args={"anchor": FIXTURE_ANCHORS["alpha_frame_w_001"]},
                          fields=("body", "etag"), headers={"mcp-replica": "w"}, lease=query["lease_id"])
    assert result["ok"] and session.trace[-1]["mutation"]["applied"]
    assert session.trace[-1]["decision"]["verdict"] == "forward" and result["replica"] == "c"
    actual = FIXTURE_ANCHORS["alpha_frame_c_001"] if scope == "content" else FIXTURE_ANCHORS["alpha_frame_w_001"]
    assert result["anchors"] == [actual] and result["rows"][0]["body"] == session.world.page(actual).body
    session.evidence(record_property, "GAP: post-call replica mutation is observable but not verified by Gateway.decide.")
