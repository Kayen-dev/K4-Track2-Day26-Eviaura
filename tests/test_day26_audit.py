from tools.audit_day26 import lethality_warnings


def test_full_match_lethality_requires_rookie_to_fall_and_adversary_to_survive():
    spar = [
        {"bot": "rookie", "role": "attacker", "seed": 4, "hp_bot": 100,
         "result": "RESULT: DRAW   you 100 — 100 rookie"},
        {"bot": "rookie", "role": "all", "seed": 4, "hp_bot": 100,
         "result": "RESULT: DRAW   you 100 — 100 rookie"},
        {"bot": "adversary", "role": "all", "seed": 4, "hp_bot": 20,
         "result": "RESULT: YOU   you 40 — 20 adversary"},
    ]
    assert len(lethality_warnings(spar)) == 1
    assert "rookie" in lethality_warnings(spar)[0]
    spar[1]["hp_bot"] = 0
    assert lethality_warnings(spar) == []
    spar[2]["hp_bot"] = 0
    assert "adversary" in lethality_warnings(spar)[0]
