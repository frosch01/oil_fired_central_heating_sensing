import io
import copy
import logging

class EventCollectRecorder(): 
    def __init__(self, path, cache_duration = 2):
        self.ostream = open(path, "r+", encoding="utf-8")
        self.ostream.seek(0, io.SEEK_END)
        self.cache_duration = cache_duration
        self.event_head = {"Time" : 0}
        self.event_tail = copy.copy(self.event_head)
        self.source_from_pos_lookup = ["Time"]
        self.event_cache = []
    
    def __del__(self):
        try:
            self.__dump_events()
            self.ostream.close()
        except:
            pass
    
    def register_event_source(self, source, pos, default):
        # Ensure there are enough positions in list
        self.source_from_pos_lookup.extend([None] * (pos + 1 - len(self.source_from_pos_lookup)))
        # Check if position is used already
        if self.source_from_pos_lookup[pos]:
            raise Exception("Event registration for source {} failed: Position {} is already given to source {}"
                            .format(source, pos, self.source_from_pos_lookup[pos]))
        # Check if source key is used already
        if source in self.event_head:
            raise Exception("Event registration for source {} failed: Source already in use".format(source))
        self.source_from_pos_lookup[pos] = source
        self.__propagate_event(source, -1, default)
    
    def create_event(self, source, time, message):
        if not source in self.event_head:
            raise Exception("Event creation failed: Source {} is not registered"
                            .format(source))
        if time < self.event_head["Time"] - self.cache_duration:
            raise Exception("Event creation failed: Time ({}) outside of cache ({})"
                            .format(time, self.event_cache))
        if time > self.event_head["Time"]:
            self.__append_event(source, time, message)
        else:
            self.__insert_event(source, time, message)
        logging.debug("{} @ {} -> {}".format(source, time, self.event_cache))
        
    def __append_event(self, source, time, message):
        logging.info("Inserting event at head")
        self.event_head[source] = message
        self.event_head["Time"] = time
        self.event_cache.append(copy.copy(self.event_head))
        self.__dump_events(time - self.cache_duration)
                
    def __insert_event(self, source, time, message):
        for cur_num, current in enumerate(self.event_cache):
            if time <= current["Time"]: break
        else:
            raise Exception("Internal error: Order of events is not plausible".format(source))
        # In case cache entry for given time exists already, just update
        if time == current["Time"]:
            logging.info("Updating existing at {}".format(cur_num))
        else:
            logging.info("Inserting before {}".format(cur_num))
            if cur_num:
                new_event = copy.copy(self.event_cache[cur_num - 1])
            else:
                new_event = copy.copy(self.event_tail)
            new_event["Time"] = time
            self.event_cache.insert(cur_num, new_event)
        self.__propagate_event(source, cur_num, message)
    
    def __propagate_event(self, source, cache_entry_num, new_message):
        """Propagate event change from tail through cache until head. 
        Propagation is stopped when a more recent event update happended already. 
        Propagation will also propagate missing sources in the cache
        """
        if (-1 == cache_entry_num):
            current_message = self.event_tail.get(source)
            self.event_tail[source] = new_message
            cache_entry_num = 0
        else:
            current_message = self.event_cache[cache_entry_num].get(source)
        # Propagate in cache as long as message in cache is the same. A different 
        # message indicates that there has been already an event creation for the 
        # time of the cache entry
        for current in self.event_cache[cache_entry_num:]:
            if current.get(source) == current_message:
                current[source] = new_message
            else: break
        else:
            self.event_head[source] = new_message
    
    def __dump_events(self, time = None):
        num = 0
        for num, event in enumerate(self.event_cache):
            if (time is None) or (time > event["Time"]):
                self.event_tail = event
                text = self.format_event(event)
                self.ostream.write(text + '\n')
            else: break
        else:
            num += 1
        if num:
            self.event_cache = self.event_cache[num:]
            self.ostream.flush()
        return num
                            
    def format_event(self, event):
        text = ""
        for source in self.source_from_pos_lookup:
            if source:
                text += str(event[source]) + " "
        return text[:-1]
