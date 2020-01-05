import io
import os
import copy
import logging

class EventCollectRecorder(): 
    def __init__(self, path, cache_duration = 2):
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
        except:
            pass
    
    def register_event_source(self, source, pos, default):
        logging.info("Registering event source {} at position {}".format(source, pos))
        # Ensure there are enough positions in list
        self._source_from_pos_lookup.extend([None] * (pos + 1 - len(self._source_from_pos_lookup)))
        # Check if position is used already
        if self._source_from_pos_lookup[pos]:
            raise Exception("Event registration for source {} failed: Position {} is already given to source {}"
                            .format(source, pos, self._source_from_pos_lookup[pos]))
        # Check if source key is used already
        if source in self._head:
            raise Exception("Event registration for source {} failed: Source already in use".format(source))
        self._source_from_pos_lookup[pos] = source
        self._propagate_event(source, -1, default)
    
    def create_event(self, source, time, event):
        if not source in self._head:
            raise Exception("Event creation failed: Source {} is not registered"
                            .format(source))
        if time < self._head["Time"] - self._cache_duration:
            raise Exception("Event creation failed: Time ({}) outside of _cache ({})"
                            .format(time, self._cache))
        if time > self._head["Time"]:
            self._append_event(source, time, event)
        else:
            self._insert_event(source, time, event)
        logging.debug("{} @ {} -> {}".format(source, time, self._cache))
        
    def _append_event(self, source, time, event):
        logging.info("Inserting event at head")
        self._head[source] = event
        self._head["Time"] = time
        self._cache.append(copy.copy(self._head))
        self._dump_events(time - self._cache_duration)
                
    def _insert_event(self, source, time, event):
        for cur_num, current in enumerate(self._cache):
            if time <= current["Time"]: break
        else:
            raise Exception("Internal error: Order of events is not plausible".format(source))
        # In case _cache entry for given time exists already, just update
        if time == current["Time"]:
            logging.info("Updating existing at {}".format(cur_num))
        else:
            logging.info("Inserting before {}".format(cur_num))
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
        if (-1 == cache_entry_num):
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
    
    def _dump_events(self, time = None):
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
