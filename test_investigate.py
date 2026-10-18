
import json
from unittest.mock import patch

from investigate import ask_ai


def test_ai_analysis_returns_response():
    fake_response = {
        "response": (
            "1. Observed facts\n"
            "2. Service dependencies\n"
            "3. Most likely hypothesis\n"
            "4. Why the hypothesis needs verification\n"
            "5. Recommended next checks"
        )
    }

    with patch("investigate.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            json.dumps(fake_response).encode("utf-8")
        )

        result = ask_ai({"incident_id": "INC-1042"})

    assert result is not None
    assert "Observed facts" in result
    assert "Most likely hypothesis" in result
    assert "Recommended next checks" in result

from falkordb import FalkorDB


def test_incident_evidence_exists():
    db = FalkorDB(host="localhost", port=6379)
    graph = db.select_graph("incidents")

    result = graph.query("""
        MATCH (i:Incident {id: 'INC-1042'})
              -[:TRIGGERED_BY]->(a:Alert)
              -[:AFFECTS]->(s:Service)
        RETURN i.id, a.severity, s.name
    """)

    assert result.result_set, "Expected incident evidence was not found"

    row = result.result_set[0]
    assert row[0] == "INC-1042"
    assert row[1] == "critical"
    assert row[2] == "Payment"


def test_payment_database_dependency_exists():
    db = FalkorDB(host="localhost", port=6379)
    graph = db.select_graph("incidents")

    result = graph.query("""
        MATCH (:Service {name: 'Payment'})
              -[:CALLS]->(dependency:Service)
        RETURN collect(dependency.name)
    """)

    assert result.result_set, "Dependency query returned no result"
    dependencies = result.result_set[0][0] or []
    assert "Database" in dependencies

def test_payment_reaches_database_through_dependency_path():
    db = FalkorDB(host="localhost", port=6379)
    graph = db.select_graph("incidents")

    result = graph.query("""
        MATCH path = (:Service {name: 'Payment'})
                     -[:CALLS*1..3]->(dependency:Service)
        RETURN collect(DISTINCT dependency.name)
    """)

    assert result.result_set, "Dependency traversal returned no result"
    dependencies = result.result_set[0][0] or []
    assert "Database" in dependencies

def test_analysis_has_all_required_sections():
    from investigate import ask_ai

    fake_analysis = (
        "1. Observed facts\n"
        "2. Service dependencies\n"
        "3. Most likely hypothesis\n"
        "4. Why the hypothesis needs verification\n"
        "5. Recommended next checks"
    )

    assert "Observed facts" in fake_analysis
    assert "Service dependencies" in fake_analysis
    assert "Most likely hypothesis" in fake_analysis
    assert "verification" in fake_analysis
    assert "Recommended next checks" in fake_analysis
