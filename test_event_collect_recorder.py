#!/usr/bin/env python3
from test_exec import *
from event_collect_recorder import *

def test_registration_pos_0(exec):
    """Position 0 is used for time, so an exception is expected if position
    0 is used for some user event
    """
    rec = EventCollectRecorder("./test.txt")
    exec.call_except(lambda: rec.register_event_source("SRC1", 0, "test1"), Exception)

def test_same_event_position(exec):
    """ Only a single event is accepted at a given position"""
    rec = EventCollectRecorder("./test.txt")
    exec.call_except(lambda: rec.register_event_source("SRC1", 1, "test1"), None)
    exec.call_except(lambda: rec.register_event_source("SRC2", 1, "test2"), Exception)
    
def test_emtpy_positions(exec):
    """As a high position is selected, other events have to be None but calling 
    format_event should not fail
    """
    rec = EventCollectRecorder("./test.txt")
    rec.register_event_source("SRC10", 10, "test10")
    rec.format_event(rec.event_map)
    
    print(rec.source_from_pos_lookup)
    print(rec.event_map)
    print(rec.event_queue)

if __name__== "__main__":
    TestExec(test_registration_pos_0).execute()
    TestExec(test_same_event_position).execute()
    TestExec(test_emtpy_positions).execute()
