from common import mqtt_contract as c


def test_heartbeat_topic_builder():
    assert c.heartbeat_topic("robot") == "system/heartbeat/robot"


def test_every_node_gets_a_distinct_namespaced_heartbeat_topic():
    topics = [c.heartbeat_topic(n) for n in c.NODES]
    assert len(topics) == len(set(topics))
    assert all(t.startswith("system/heartbeat/") for t in topics)


def test_timeout_leaves_room_for_a_missed_heartbeat():
    """A single dropped packet must not flip a node to 'down' on the phone."""
    assert c.HEARTBEAT_TIMEOUT >= 2 * c.HEARTBEAT_SECONDS
