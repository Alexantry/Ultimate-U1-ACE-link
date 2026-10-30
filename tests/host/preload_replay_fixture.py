"""Virtual-time preload tests using framed heartbeat replies, never real hardware."""
import unittest
from test_protocol import new, frame, Serial, mod


class Replay:
    def __init__(self, ready_at=145., inserted=(0,), gate_fn=None):
        self.ace = new()
        self.ace.feed_length = 1250
        self.ace.feed_speed = 200
        self.ready_at = ready_at
        self.inserted = inserted
        self.gate_fn = gate_fn
        self.feed_end = 0.
        self.feeds = []
        self.commands = []
        self.drop_feed_ack = False
        self.reject_feed = False
        self.never_finish = False
        self.on_feed = None
        self.ace._serial.reply = self.reply
        self.ace.reactor.pending.append((100., self.tick))

    def loaded(self, now):
        if self.gate_fn is not None: return self.gate_fn(now)
        return self.inserted if now >= 101. else ()

    def reply(self, request):
        a = self.ace; now = a.reactor.t
        self.commands.append((now, request.copy()))
        method = request['method']
        if method == 'get_status':
            busy = now >= 101. and (now < self.ready_at or now < self.feed_end)
            loaded = self.loaded(now)
            return {'id':request['id'],'code':0,'result': {
                'status':'busy' if busy else 'ready',
                'slots':[{'index':i,'status':'ready' if i in loaded else 'empty',
                          'rfid':1,'sku':'','type':'','color':[0,0,0]} for i in range(4)]}}
        if method == 'feed_filament':
            self.feeds.append((now, request['params'].copy()))
            self.feed_end = float('inf') if self.never_finish else now + request['params']['length']/request['params']['speed']
            if self.on_feed is not None: self.on_feed(request)
            if self.drop_feed_ack: return None
            return {'id':request['id'],'code':12 if self.reject_feed else 0,
                    'msg':'rejected' if self.reject_feed else 'success'}
        if method == 'stop_feed_filament': self.feed_end = now
        return {'id':request['id'],'code':0,'msg':'success'}

    def tick(self):
        a = self.ace
        if a._connected: a._periodic_heartbeat_event(a.reactor.t)
        a.reactor.pending.append((a.reactor.t + 1., self.tick))

    def start(self):
        self.ace.reactor.pause(101.1)
        return self.ace

    def drain(self):
        while self.ace.reactor.asyncs:
            self.ace.reactor.asyncs.pop(0)(self.ace.reactor.t)

