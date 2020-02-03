
""" Provides implementation of the class EventCollectRecorder, an event recoreder that created as
simple, space separated table from single events """

import copy
import logging

class EventCollectRecorder():
    """EventCollectRecorder implements an recorder that logs events into a regular text file. On
    each arrival of an event (with a new time) a line is written into the log file. In each line
    all the states of the events are printed. Like this, a space separated value list is created
    that can be used by many tools, e.g. gnuplot or libreoffice.
    Bevor an event can be repoted is has to be registered which typically should happen before the
    first event occurs to ensure that all the lines have the same content from the start. During
    registration an event also gets assigned a source (for identification) and a column where it
    will be printed inside the lines. Along with each event a timestamp has to be provided that
    clearly gives the events the right order. As processing perhaps happens in an unpredictible
    order events perhaps are not deliverd exactly in the timely order. To compensate from a
    certain amount of nonlinear processing, the class maintains a time based cache. When an
    event occurs that is located in the past, it will be sorted at the right position in the
    cache. As long as event are in the cache they may be also overwritten with updated data.
    Also, a grouping of events can be achieved when the events are reported using identical
    timestamp.
    """

    def __init__(self, path, cache_duration=2):
        self._ostream = open(path, "a", encoding="utf-8")
        self._cache_duration = cache_duration
        self._head = {"Time" : 0}
        self._tail = copy.copy(self._head)
        self._cache = []
        self._source_from_pos_lookup = ["Time"]

    def __del__(self):
        try:
            self._dump_events()
            self._ostream.close()
        except BaseException:
            pass

    def register_event_source(self, source, pos, default):
        """ Register a new event from the given source to be printed as pos culumn in the text
        lines. Source and pos has to be unique for each event. Until the event occures the first
        time, the default value is used for event state.

        Arguments:
        source  -- The event source, unique key for identification of the event
        pos     -- The columnt number the event is prints in the output lines
        default -- The value of event state until the event is received the fist time
        """

        logging.info("Registering event source %s at position %d", source, pos)
        # Ensure there are enough positions in list
        self._source_from_pos_lookup.extend([None] * (pos + 1 - len(self._source_from_pos_lookup)))
        # Check if position is used already
        if self._source_from_pos_lookup[pos]:
            raise Exception("Event registration for source {} failed: "
                            "Position {} is already given to source {}"
                            .format(source, pos, self._source_from_pos_lookup[pos]))
        # Check if source key is used already
        if source in self._head:
            raise Exception("Event registration for source {} failed: Source already in use"
                            .format(source))
        self._source_from_pos_lookup[pos] = source
        self._propagate_event(source, -1, default)

    def create_event(self, source, time, event):
        """ Set the state of the event from source source to event. Use time to locate the event
        in time. In case event is past the previous reported event, it will be sorted into the
        right location in the cache. Events that fall outside the cache window will be written to
        disk

        Arguments:
        source -- The event source, unique key for identification of the event
        time   -- Location of the event in time
        event  -- The event value
        """
        logging.info("New event time:source:event %f:%s:%s", time, source, str(event))
        if source not in self._head:
            raise Exception("Event creation failed: Source {} is not registered"
                            .format(source))
        if time < self._head["Time"] - self._cache_duration:
            raise Exception("Event creation failed: Time ({}) outside of _cache ({})"
                            .format(time, self._cache))
        if time > self._head["Time"]:
            self._append_event(source, time, event)
        else:
            self._insert_event(source, time, event)
        logging.debug("%s @ %f -> %s", source, time, str(self._cache))

    def _append_event(self, source, time, event):
        logging.debug("Inserting event at head")
        self._head[source] = event
        self._head["Time"] = time
        self._cache.append(copy.copy(self._head))
        self._dump_events(time - self._cache_duration)

    def _insert_event(self, source, time, event):
        cur_num = -1
        current = None
        for cur_num, current in enumerate(self._cache):
            if time <= current["Time"]:
                break
        else:
            raise Exception("Internal error: Order of events is not plausible")
        # In case _cache entry for given time exists already, just update
        if time == current["Time"]:
            logging.debug("Updating existing at %d", cur_num)
        else:
            logging.debug("Inserting before %d", cur_num)
            if cur_num:
                new_event = copy.copy(self._cache[cur_num - 1])
            else:
                new_event = copy.copy(self._tail)
            new_event["Time"] = time
            self._cache.insert(cur_num, new_event)
        self._propagate_event(source, cur_num, event)

    def _propagate_event(self, source, cache_entry_num, new_message):
        """Propagate event change from tail through _cache until head.
        Propagation is stopped when a more recent event update happended already.
        Propagation will also propagate missing sources in the _cache
        """
        if -1 == cache_entry_num:
            current_message = self._tail.get(source)
            self._tail[source] = new_message
            cache_entry_num = 0
        else:
            current_message = self._cache[cache_entry_num].get(source)
        # Propagate in _cache as long as event in _cache is the same. A different
        # event indicates that there has been already an event creation for the
        # time of the _cache entry
        for current in self._cache[cache_entry_num:]:
            if current.get(source) == current_message:
                current[source] = new_message
            else: break
        else:
            self._head[source] = new_message

    def _dump_events(self, time=None):
        num = 0
        for num, event in enumerate(self._cache):
            if (time is None) or (time > event["Time"]):
                self._tail = event
                text = self._format_event(event)
                self._ostream.write(text + '\n')
            else: break
        else:
            num += 1
        if num:
            self._cache = self._cache[num:]
            self._ostream.flush()
        return num

    def _format_event(self, event):
        text = ""
        for source in self._source_from_pos_lookup:
            if source:
                text += str(event[source]) + " "
        return text[:-1]
