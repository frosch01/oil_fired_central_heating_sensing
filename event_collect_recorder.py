import io
import copy

class EventCollectRecorder(): 
    def __init__(self, path, cache_duration = 2):
        self.ostream = open(path, "w", encoding="utf-8")
        self.ostream.seek(0, io.SEEK_END)
        self.cache_duration = cache_duration
        self.event_map  = {"Time" : 0}
        self.source_from_pos_lookup = ["Time"]
        self.event_queue = []
    
    def __del__(self):
        try:
            for event in self.event_queue:
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
        self.source_from_pos_lookup[pos] = source
        self.event_map[source] = default
    
    def create_event(self, source, time, message):
        self.event_map[source] = message
        self.event_map["Time"] = time
        for num, event in enumerate(self.event_queue):
            if time < event["Time"]:
                self.event_queue.insert(num, copy.copy(self.event_map))
        self.dump_events(time - self.cache_duration)
                
    def update_event(self, source, time, message):
        success = False
        for event in self.event_queue:
            if time == event["Time"]:
                event[source] = message
                success = True
                break
        if not success:
            raise Exception("Event update of source {} failed: Time {} not in queue [{}..{}]"
                            .format(source, time, self.event_queue[0], self.event_queue[-1]))
                            
    def dump_events(self, time = 0):
        for num, event in enumerate(self.event_queue):
            if (time == 0) or (time > event["Time"]):
                text = self.format_event(event)
                self.ostream.write(text + '\n')
            else:
                for pos in range(num): 
                    self.event_queue.pop(pos)
                break
        return num
                            
    def format_event(self, event):
        text = ""
        for source in self.source_from_pos_lookup:
            if source:
                text += str(event[source]) + " "
        return text[:-1]
