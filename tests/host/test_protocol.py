"""Independent simulated serial protocol checks. No network/device access."""
from pathlib import Path
import importlib.util, types, sys, json, struct, unittest

serial=types.ModuleType('serial')
serial.SerialException=type('SerialException',(Exception,),{})
serial.serialutil=types.SimpleNamespace(SerialException=serial.SerialException)
sys.modules['serial']=serial
source=Path(__file__).resolve().parents[2]/'payload/ace.py'
spec=importlib.util.spec_from_file_location('ported_ace',source)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class Reactor:
    NOW=0.;NEVER=float('inf')
    def __init__(self):self.t=100.;self.pending=[];self.asyncs=[];self.timers=[]
    def monotonic(self):return self.t
    def pause(self,target):
        assert target>=self.t
        while any(t<=target for t,cb in self.pending):
            t,cb=min(self.pending,key=lambda x:x[0]);self.pending.remove((t,cb));self.t=t;cb()
        self.t=target
    def register_async_callback(self,cb):self.asyncs.append(cb)
    def register_timer(self,cb,when=None):self.timers.append((cb,when));return cb
    def unregister_timer(self,handle):pass
    def register_fd(self,fd,cb):return fd
    def unregister_fd(self,fd):pass

class Gcode:
    def __init__(self):self.messages=[];self.scripts=[]
    def respond_raw(self,s):self.messages.append(s)
    def respond_info(self,s):self.messages.append(s)
    def run_script_from_command(self,s):self.scripts.append(s)
    def register_command(self,*a,**k):pass

class Printer:
    def __init__(self):
        self.reactor=Reactor();self.gcode=Gcode()
        self.events=[];self._event_handlers={}
    def get_reactor(self):return self.reactor
    def lookup_object(self,name,default=None):
        if name=='gcode':return self.gcode
        if name=='save_variables':return types.SimpleNamespace(allVariables={'ace__revision':1})
        return default
    def register_event_handler(self,name,callback):
        self._event_handlers.setdefault(name,[]).append(callback)
    def send_event(self,name,*args):
        self.events.append((name,*args))
        return [callback(*args) for callback in self._event_handlers.get(name,[])]

class Config:
    def __init__(self):self.printer=Printer()
    def get_printer(self):return self.printer
    def get_name(self):return 'ace'
    def get(self,k,default=None):return default
    def getint(self,k,default=None,**bounds):return default
    def error(self,s):raise RuntimeError(s)

def frame(ace,response):
    payload=json.dumps(response).encode()
    return b'\xff\xaa'+struct.pack('<H',len(payload))+payload+struct.pack('<H',mod.BunnyAce._calc_crc(ace,payload))+b'\xfe'

class Serial:
    def __init__(self,ace):self.ace=ace;self.is_open=True;self.sent=[];self.reply=None;self.short=False
    def close(self):self.is_open=False
    def fileno(self):return 1
    def write(self,data):
        count=struct.unpack('<H',data[2:4])[0];request=json.loads(data[4:4+count]);self.sent.append(request)
        if self.short:return len(data)-1
        if self.reply:
            response=self.reply(request)
            if response is not None:
                self.ace.reactor.pending.append((self.ace.reactor.t+.01,lambda:self.ace._process_data(frame(self.ace,response))))
        return len(data)

def new():
    ace=mod.BunnyAce(Config());ace._serial=Serial(ace);ace._connected=True
    ace._last_status_time=ace.reactor.t;ace._connected_at=ace.reactor.t
    ace._last_status_epoch=ace._status_epoch
    return ace

class ProtocolChecks(unittest.TestCase):
    def test_command_waits_for_matching_reply(self):
        a=new();a._serial.reply=lambda r:{'id':r['id'],'code':0,'msg':'success'}
        self.assertEqual(a._command({'method':'start_feed_assist','params':{'index':1}})['code'],0)
        self.assertGreater(a.reactor.t,100.)
        self.assertEqual(a._callback_map,{})

    def test_device_error_propagates(self):
        a=new();a._serial.reply=lambda r:{'id':r['id'],'code':12,'msg':'jam'}
        with self.assertRaises(mod.AceException):a._command({'method':'start_feed_assist','params':{'index':0}})
        self.assertLess(a.reactor.t,101.)

    def test_missing_ack_times_out_and_late_ack_is_ignored(self):
        a=new()
        with self.assertRaises(mod.AceException):a._command({'method':'start_feed_assist','params':{'index':1}})
        self.assertGreaterEqual(a.reactor.t,105.)
        self.assertLess(a.reactor.t,105.2)
        self.assertEqual(a._callback_map,{})
        a._process_data(frame(a,{'id':a._request_id,'code':0,'msg':'success'}))
        self.assertEqual(a._callback_map,{})

    def test_unmatched_ack_is_not_success(self):
        a=new();a._serial.reply=lambda r:{'id':r['id']+99,'code':0}
        with self.assertRaises(mod.AceException):a._command({'method':'stop_feed_filament','params':{'index':1}},ready=False)

    def test_partial_serial_write_disconnects(self):
        a=new();a._serial.short=True
        with self.assertRaises(mod.AceException):a._command({'method':'stop_feed_filament','params':{'index':1}},ready=False)
        self.assertFalse(a._connected);self.assertEqual(a._callback_map,{})

    def test_stale_ready_never_sends_motion(self):
        a=new();a._last_status_time=90.
        with self.assertRaises(mod.AceException):a._command({'method':'start_feed_assist','params':{'index':1}})
        self.assertEqual(a._serial.sent,[])

    def test_crc_renumber_keeps_response_callback(self):
        a=new();count=[0];real=a._calc_crc
        def crc(data):
            count[0]+=1
            return 0xaaff if count[0]==1 else real(data)
        a._calc_crc=crc;a._serial.reply=lambda r:{'id':r['id'],'code':0}
        result=a._command({'method':'stop_feed_filament','params':{'index':0}},ready=False)
        self.assertEqual(result['id'],2);self.assertEqual(a._callback_map,{})

    def test_startup_loaded_gates_do_not_feed(self):
        a=new();a._serial.reply=lambda r:{'id':r['id'],'code':0,'result':{'status':'ready','slots':[{'status':'loaded','rfid':0} for _ in range(4)]}}
        a._periodic_heartbeat_event(a.reactor.t);a.reactor.pause(100.1)
        self.assertEqual(a.gate_status,[1]*4)
        self.assertEqual(a.reactor.asyncs,[])
        self.assertEqual([r['method'] for r in a._serial.sent],['get_status'])

    def test_heartbeat_does_not_mark_ready_busy(self):
        a=new();a._periodic_heartbeat_event(a.reactor.t)
        self.assertEqual(a._info['status'],'ready')

    def test_reconnect_never_resumes_feed_assist(self):
        a=new();a._feed_assist_index=2;transport=Serial(a)
        serial.Serial=lambda **kw:transport
        a._connect(a.reactor.t)
        self.assertEqual([r['method'] for r in transport.sent],['get_info'])

    def test_initial_disable_never_sends_negative_channel(self):
        a=new();a._disable_feed_assist()
        self.assertEqual(a._serial.sent,[])

    def test_rejected_assist_start_raises_and_attempts_stop(self):
        a=new();a._serial.reply=lambda r:{'id':r['id'],'code':12 if r['method']=='start_feed_assist' else 0,'msg':'jam' if r['method']=='start_feed_assist' else 'success'}
        with self.assertRaises(mod.AceException):a._enable_feed_assist(2)
        self.assertEqual([r['method'] for r in a._serial.sent],['start_feed_assist','stop_feed_assist'])
        self.assertEqual(a._feed_assist_index,-1)

    def test_rejected_assist_stop_never_retracts(self):
        a=new();a._feed_assist_index=2;a._serial.reply=lambda r:{'id':r['id'],'code':12,'msg':'jam'}
        with self.assertRaises(mod.AceException):a._disable_feed_assist()
        self.assertEqual([r['method'] for r in a._serial.sent],['stop_feed_assist'])
        self.assertEqual(a._feed_assist_index,2)

    def test_rejected_feed_attempts_stop_and_raises(self):
        a=new();a._serial.reply=lambda r:{'id':r['id'],'code':12 if r['method']=='feed_filament' else 0,'msg':'jam'}
        with self.assertRaises(mod.AceException):a._feed(2,100,20,0)
        self.assertEqual([r['method'] for r in a._serial.sent],['feed_filament','stop_feed_filament'])

    def test_negative_channel_is_never_sent(self):
        a=new()
        for action in (lambda:a._feed(-1,100,20),lambda:a._retract(-1,100,20),lambda:a._stop_feeding(-1),lambda:a._enable_feed_assist(-1)):
            with self.assertRaises(mod.AceException):action()
        self.assertEqual(a._serial.sent,[])

if __name__=='__main__':unittest.main(verbosity=2)
