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


def test_robot_topics_are_distinct_and_namespaced():
    topics = [c.ROBOT_DRIVE, c.ROBOT_SPEED, c.ROBOT_LIGHTS, c.ROBOT_LOCK]
    assert len(set(topics)) == len(topics)
    assert all(t.startswith("robot/") for t in topics)


def test_the_four_directions_and_a_stop():
    assert set(c.DRIVE_COMMANDS) == {"forward", "back", "left", "right", "stop"}


def test_the_robot_stops_before_it_misses_more_than_two_repeats():
    """The timeout must exceed the repeat gap, or the robot stutters while a
    button is held; but it must stay short enough that letting go stops it
    promptly."""
    assert c.DRIVE_REPEAT_MS < c.DRIVE_TIMEOUT_MS <= 3 * c.DRIVE_REPEAT_MS
