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
        self.event_queue = []
    
    def __del__(self):
        try:
            self.dump_events()
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
        self.event_head[source] = default
        self.event_tail = copy.copy(self.event_head)
    
    def create_event(self, source, time, message):
        if not source in self.event_head:
            raise Exception("Event creation failed: Source {} is not registered"
                            .format(source))
        if time < self.event_head["Time"] - self.cache_duration:
            raise Exception("Event creation failed: Time ({}) outside of cache ({})"
                            .format(time, self.event_queue))
        if time > self.event_head["Time"]:
            logging.info("Inserting event at head")
            self.event_head[source] = message
            self.event_head["Time"] = time
            self.event_queue.append(copy.copy(self.event_head))
            self.dump_events(time - self.cache_duration)
        else:
            self.__update_propagate(source, time, message)
        logging.debug("{} @ {} -> {}".format(source, time, self.event_queue))
                
    def __update_propagate(self, source, time, message):
        cur_num = -1
        prev = None
        for cur_num, current in enumerate(self.event_queue):
            if time <= current["Time"]: break
            prev = current
        else:
            raise Exception("Internal error: Order of events is not plausible".format(source))
        # in case entry for given time exists already, just update
        current_message = current[source]
        if time == current["Time"]:
            logging.info("Updating existing at {}".format(cur_num))
            current[source] = message
        else:
            if prev:
                logging.info("Inserting after {}".format(cur_num - 1))
                new_event = copy.copy(prev)
            else:
                logging.info("Inserting at tail")
                new_event = copy.copy(self.event_tail)
            new_event[source] = message
            new_event["Time"] = time
            self.event_queue.insert(cur_num, new_event)
        # Propagate update in cache and head. Propagation is stopped when 
        # a more recent event is found
        for current in self.event_queue[cur_num + 1:]:
            if current[source] == current_message:
                current[source] = message
            else: break
        else:
            self.event_head[source] = message
                    
    def dump_events(self, time = None):
        num = 0
        for num, event in enumerate(self.event_queue):
            if (time is None) or (time > event["Time"]):
                self.event_tail = event
                text = self.format_event(event)
                self.ostream.write(text + '\n')
            else: break
        else:
            num += 1
        if num:
            self.event_queue = self.event_queue[num:]
            self.ostream.flush()
        return num
                            
    def format_event(self, event):
        text = ""
        for source in self.source_from_pos_lookup:
            if source:
                text += str(event[source]) + " "
        return text[:-1]

