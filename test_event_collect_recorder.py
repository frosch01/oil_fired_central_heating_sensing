#!/usr/bin/env python3
import os
from test_exec import *
from event_collect_recorder import *

def test_registration_pos_0(exec):
    """Position 0 is used for time, so an exception is expected if position
    0 is used for some user event
    """
    rec = EventCollectRecorder("./test.txt")
    exec.call_except(lambda: rec.register_event_source("SRC1", 0, "test1"), Exception)

def test_unique(exec):
    """ Only a single event is accepted at a given position"""
    rec = EventCollectRecorder("./test.txt")
    exec.call_except(lambda: rec.register_event_source("SRC1", 1, "test1"), None)
    exec.call_except(lambda: rec.register_event_source("SRC2", 1, "test2"), Exception)
    exec.call_except(lambda: rec.register_event_source("SRC1", 2, "test1"), Exception)
    
def test_emtpy_positions(exec):
    """As a high position is selected, other events have to be None but calling 
    format_event should not fail
    """
    rec = EventCollectRecorder("./test.txt")
    rec.register_event_source("SRC10", 10, "test10")
    line = rec.format_event(rec.event_head)
    exec.report(line == "0 test10", "Event formatting")    
    
def test_position_ordering(exec):
    """Events may be registered in arbitrary order. At the end, the log entry 
    shall follow the orering given as position during test_registration. Also,
    the default string shall be used as entries if no event has been created
    """
    rec = EventCollectRecorder("./test.txt")
    rec.register_event_source("SRC3", 3, "test3")
    rec.register_event_source("SRC2", 2, "test2")
    rec.register_event_source("SRC1", 1, "test1")
    line = rec.format_event(rec.event_head)
    exec.report(line == "0 test1 test2 test3", "Output position")
    
def test_event_ordered(exec):
    """Test event creation and caching with timely ordered events"""
    rec = EventCollectRecorder("./test.txt", 2)
    rec.register_event_source("SRC1", 1, "init1")
    rec.register_event_source("SRC2", 2, "init2")
    rec.register_event_source("SRC3", 3, "init3")
    # Try to create an event for an unregistered source
    exec.call_except(lambda: rec.create_event("SRC4", 1.0, "update4"), Exception)
    # Check expected usage
    rec.create_event("SRC1", 1.0, "event1")
    rec.create_event("SRC2", 1.5, "event2")
    rec.create_event("SRC3", 2.0, "event3")
    queue_len = len(rec.event_queue)
    exec.report(queue_len == 3, "Event in queue ({}) == 3".format(queue_len))
    time_expected=[1.0, 1.5, 2.0]
    for event, expected in zip(rec.event_queue, time_expected):
        exec.report(event["Time"] == expected, "Events are stored in timely order")

def test_event_unordered(exec):
    """Test event creation and caching with timely out of order events.
    Updates done before head are expected to be propagated to the head
    """
    rec = EventCollectRecorder("./test.txt", 2)
    rec.register_event_source("SRC1", 1, "init1")
    rec.register_event_source("SRC2", 2, "init2")
    rec.register_event_source("SRC3", 3, "init3")
    rec.create_event("SRC1", 2.0, "event1")
    rec.create_event("SRC2", 1.0, "event2")
    expected = [{'Time':1.0, 'SRC1':'init1',  'SRC2':'event2', 'SRC3':'init3'}, 
                {'Time':2.0, 'SRC1':'event1', 'SRC2':'event2', 'SRC3':'init3'}]
    exec.report(rec.event_queue == expected, "Expected queue after inserting before head")
    rec.create_event("SRC3", 1.5, "event3")
    expected = [{'Time':1.0, 'SRC1':'init1',  'SRC2':'event2', 'SRC3':'init3'}, 
                {'Time':1.5, 'SRC1':'init1',  'SRC2':'event2', 'SRC3':'event3'},
                {'Time':2.0, 'SRC1':'event1', 'SRC2':'event2', 'SRC3':'event3'}]
    exec.report(rec.event_queue == expected, "Expected queue after inserting in between")
    rec.create_event("SRC1", 2.5, "event1_1")
    expected = [{'Time':1.0, 'SRC1':'init1',    'SRC2':'event2', 'SRC3':'init3'}, 
                {'Time':1.5, 'SRC1':'init1',    'SRC2':'event2', 'SRC3':'event3'},
                {'Time':2.0, 'SRC1':'event1',   'SRC2':'event2', 'SRC3':'event3'},
                {'Time':2.5, 'SRC1':'event1_1', 'SRC2':'event2', 'SRC3':'event3'}]
    exec.report(rec.event_queue == expected, "Expected queue after inserting at head")
        
def test_dump_on_time_exceed(exec):
    """Test event dump/cache removal as storage time exceeds"""
    rec = EventCollectRecorder("./test.txt", 2)
    rec.register_event_source("SRC1", 1, "init1")
    rec.register_event_source("SRC2", 2, "init2")
    rec.create_event("SRC1", 1.0, "event1_1")
    rec.create_event("SRC2", 2.0, "event2_1")
    rec.create_event("SRC1", 3.0, "event1_2")
    rec.create_event("SRC2", 4.1, "event2_2")
    queue_len = len(rec.event_queue)
    exec.report(queue_len == 2, "Event in queue ({}) == 2".format(queue_len))
    time_expected=[3.0, 4.1]
    for event, expected in zip(rec.event_queue, time_expected):
        exec.report(event["Time"] == expected, "Events are stored in timely order")
        
def test_update_event(exec):
    """Test for updating events in the cache
    Updates before are expected to be propagated towards head as long as there 
    has not been stored another event of same source
    """
    rec = EventCollectRecorder("./test.txt", 2)
    rec.register_event_source("SRC1", 1, "init1")
    rec.register_event_source("SRC2", 2, "init2")
    rec.register_event_source("SRC3", 3, "init3")
    # Add events and check content
    rec.create_event("SRC1", 1.0, "event1")
    rec.create_event("SRC2", 2.0, "event2")
    rec.create_event("SRC3", 3.0, "event3")
    expected = [{'Time':1.0, 'SRC1':'event1', 'SRC2':'init2',  'SRC3':'init3'}, 
                {'Time':2.0, 'SRC1':'event1', 'SRC2':'event2', 'SRC3':'init3'},
                {'Time':3.0, 'SRC1':'event1', 'SRC2':'event2', 'SRC3':'event3'}]
    exec.report(rec.event_queue == expected, "Expected queue content before update")
    rec.create_event("SRC2", 1.0, "update2")
    expected[0]["SRC2"] = "update2"
    exec.report(rec.event_queue == expected, "Expected update without propagation of SRC2 at time 1.0")
    rec.create_event("SRC1", 2.0, "update1")
    expected[1]["SRC1"] = "update1"
    expected[2]["SRC1"] = "update1"
    exec.report(rec.event_queue == expected, "Expected propagation after update of SRC1 at time 2.0")
    rec.create_event("SRC3", 3.0, "update3")
    expected[2]["SRC3"] = "update3"
    exec.report(rec.event_queue == expected, "Expected update of last queue element at time 3.0")

if __name__== "__main__":
    TestExec(test_registration_pos_0).execute()
    TestExec(test_unique).execute()
    TestExec(test_emtpy_positions).execute()
    TestExec(test_position_ordering).execute()
    TestExec(test_event_ordered).execute()    
    TestExec(test_event_unordered).execute()    
    TestExec(test_dump_on_time_exceed).execute()
    TestExec(test_update_event).execute()
    
