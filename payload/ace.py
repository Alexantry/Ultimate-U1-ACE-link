import logging
import json
import struct
import queue
import traceback
import serial
from serial import SerialException
from functools import wraps


class AceException(Exception):
    def __init__(self, message, command_sent=False):
        super().__init__(message)
        self.command_sent = command_sent


def ace_gcode_command(func):
    @wraps(func)
    def guarded(self, gcmd):
        try:
            if (func.__name__ in ('cmd_ACE_FEED', 'cmd_ACE_RETRACT',
                    'cmd_ACE_ENABLE_FEED_ASSIST', 'cmd_ACE_DISABLE_FEED_ASSIST')
                    and getattr(self, '_u1_load_owner', None) is not None):
                raise AceException('ACE is owned by an active U1 filament operation')
            return func(self, gcmd)
        except AceException as exc:
            raise gcmd.error(str(exc)) from exc
    return guarded


GATE_UNKNOWN = -1
GATE_EMPTY = 0
GATE_AVAILABLE = 1  # Available to load from either buffer or spool


class BunnyAce:
    VARS_ACE_REVISION = 'ace__revision'
    REQUEST_TIMEOUT = 5.0
    STATUS_TIMEOUT = 5.0
    READY_TIMEOUT = 30.0
    PORT_VERSION = 'u1-2.0.0-snapace-34a06e87-port7-forward-takeup'
    PRELOAD_WAIT_TIMEOUT = 180.0
    FAST_LOAD_LENGTH = 1150
    FAST_LOAD_SPEED = 200
    SENSOR_LOAD_SPEED = 50
    SENSOR_LOAD_MAX_LENGTH = 2500
    SENSOR_LOAD_WAIT_TIMEOUT = 180.0
    SENSOR_LOAD_FINISH_TIMEOUT = 10.0
    RFID_SYNC_ATTEMPTS = 3
    RFID_RETRY_DELAY = 2.0
    # Base types from the U1 OpenRFID valid_materials.py; suffixes stay separate.
    MATERIAL_BASE_TYPES = frozenset(('ABS ABS-CF ABS-GF ASA ASA-CF ASA-GF ASA-AERO '
        'BVOH CoPE EVA FLEX HIPS PA PA-CF PA-GF PA6 PA6-CF PA6-GF PA11 PA11-CF '
        'PA11-GF PA12 PA12-CF PA12-GF PAHT PAHT-CF PAHT-GF PC PC-ABS PC-CF PC-PBT '
        'PCL PCTG PE PE-CF PE-GF PEI-1010 PEI-1010-CF PEI-1010-GF PEI-9085 '
        'PEI-9085-CF PEI-9085-GF PEEK PEEK-CF PEEK-GF PEKK PEKK-CF PES PET PET-CF '
        'PET-GF PETG PETG-CF PETG-GF PHA PI PLA PLA-AERO PLA-CF POM PP PP-CF PP-GF '
        'PPA-CF PPA-GF PPS PPS-CF PPSU PSU PVA PVB PVDF SBS TPI TPU').split())

    def __init__(self, config):
        self._connected = False
        self._serial = None
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self._name = config.get_name()
        self.send_time = None
        self.ace_dev_fd = None
        self.heartbeat_timer = None
        self.connect_timer = None
        self._shutting_down = False
        self._last_status_time = None
        self._connected_at = None
        self._heartbeat_request = None
        self._filament_query = None
        self._rfid_sync = [None] * 4
        self._preload_generation = 0
        self._preload_jobs = {}
        self._preload_queue = []
        self._preload_worker = None
        self.error_msg = None
        self._control_inflight = False
        self._status_epoch = 0
        self._last_status_epoch = -1

        self.gate_status = [GATE_UNKNOWN, GATE_UNKNOWN, GATE_UNKNOWN, GATE_UNKNOWN]
        self._fast_origins = [None] * 4
        self._gate_epochs = [0] * 4
        self._motion_pending = set()
        self._u1_unload_depth = 0
        self._takeup_ready = None
        self.read_buffer = bytearray()
        if self._name.startswith('ace '):
            self._name = self._name[4:]

        self.save_variables = self.printer.lookup_object('save_variables', None)
        if self.save_variables:
            revision_var = self.save_variables.allVariables.get(self.VARS_ACE_REVISION, None)
            if revision_var is None:
                config.error("You have custom [save_variables]. "
                             "Copy the contents of ace_vars.cfg to your file and remove [save_variables] in ace.cfg")
        else:
            config.error("There is no [save_variables] in the config. Check installation guide")


        self.serial_id = config.get('serial', '/dev/ttyACM0')
        self.baud = config.getint('baud', 115200)

        self.feed_speed = config.getint('feed_speed', 50)
        self.retract_speed = config.getint('retract_speed', 50)
        self.retract_length = config.getint('retract_length', 100)
        self.feed_length = config.getint('feed_length', 100)
        self.forward_takeup_length = config.getint('forward_takeup_length', 0, minval=0, maxval=500)
        self.forward_takeup_speed = config.getint('forward_takeup_speed', 20, minval=1, maxval=50)
        if self.forward_takeup_length >= min(self.retract_length, self.FAST_LOAD_LENGTH):
            raise config.error('forward_takeup_length must be less than retract_length and fast-load length')
        self.max_dryer_temperature = config.getint('max_dryer_temperature', 55)

        self._callback_map = {}
        self._feed_assist_index = -1
        self._request_id = 0

        # Default data to prevent exceptions
        self._info = {
            'status': 'ready',
            'dryer_status': {
                'status': 'stop',
                'target_temp': 0,
                'duration': 0,
                'remain_time': 0
            },
            'temp': 0,
            'enable_rfid': 1,
            'fan_speed': 7000,
            'feed_assist_count': 0,
            'cont_assist_time': 0.0,
            'slots': [
                {
                    'index': 0,
                    'status': 'empty1',
                    'sku': '',
                    'type': '',
                    'rfid': 0,
                    'brand':'',
                    'color': [0, 0, 0]
                },
                {
                    'index': 1,
                    'status': 'empty1',
                    'sku': '',
                    'type': '',
                    'rfid': 0,
                    'brand': '',
                    'color': [0, 0, 0]
                },
                {
                    'index': 2,
                    'status': 'empty1',
                    'sku': '',
                    'type': '',
                    'rfid': 0,
                    'brand': '',
                    'color': [0, 0, 0]
                },
                {
                    'index': 3,
                    'status': 'empty1',
                    'sku': '',
                    'type': '',
                    'rfid': 0,
                    'brand': '',
                    'color': [0, 0, 0]
                }
            ]
        }
        self.extruder_sensor = None

        self.printer.register_event_handler('klippy:ready', self._handle_ready)
        self.printer.register_event_handler('klippy:disconnect', self._handle_disconnect)

        self.gcode.register_command(
            'ACE_START_DRYING', self.cmd_ACE_START_DRYING,
            desc=self.cmd_ACE_START_DRYING_help)
        self.gcode.register_command(
            'ACE_STOP_DRYING', self.cmd_ACE_STOP_DRYING,
            desc=self.cmd_ACE_STOP_DRYING_help)
        self.gcode.register_command(
            'ACE_ENABLE_FEED_ASSIST', self.cmd_ACE_ENABLE_FEED_ASSIST,
            desc=self.cmd_ACE_ENABLE_FEED_ASSIST_help)
        self.gcode.register_command(
            'ACE_DISABLE_FEED_ASSIST', self.cmd_ACE_DISABLE_FEED_ASSIST,
            desc=self.cmd_ACE_DISABLE_FEED_ASSIST_help)
        self.gcode.register_command(
            'ACE_FEED', self.cmd_ACE_FEED,
            desc=self.cmd_ACE_FEED_help)
        self.gcode.register_command(
            'ACE_RETRACT', self.cmd_ACE_RETRACT,
            desc=self.cmd_ACE_RETRACT_help)
        self.gcode.register_command(
            'ACE_QUERY_FILAMENT', self.cmd_ACE_QUERY_FILAMENT,
            desc=self.cmd_ACE_QUERY_FILAMENT_help)

    def _handle_ready(self):
        self.toolhead = self.printer.lookup_object('toolhead')

        logging.info(f'ACE: Connecting to {self.serial_id}')
        # We can catch timing where ACE reboots itself when no data is available from host. We're avoiding it with this hack
        self._connected = False
        self._queue = queue.Queue()
        self.connect_timer = self.reactor.register_timer(self._connect, self.reactor.NOW)

    def _handle_disconnect(self):
        logging.info(f'ACE: Closing connection to {self.serial_id}')
        self._shutting_down = True
        self._serial_disconnect()
        if self.connect_timer is not None:
            self.reactor.unregister_timer(self.connect_timer)
            self.connect_timer = None
        self._queue = None

    def _color_message(self, msg):
        try:
            html_msg = msg.format(
                '</span>',  # {0}
                '<span style="color:#FFFF00">',  # {1}
                '<span style="color:#90EE90">',  # {2}
                '<span style="color:#458EFF">',  # {3}
                '<b>',  # {5}
                '</b>'  # {6}
            )
        except (IndexError, KeyError, ValueError) as e:
            html_msg = msg
        return html_msg

    def log_warning(self, msg):
        c_msg = self._color_message(f'{{1}}{msg}{{0}}')
        self.gcode.respond_raw(c_msg)

    def log_always(self, msg: str, color=False):
        c_msg = self._color_message(msg) if color else msg
        self.gcode.respond_raw(c_msg)

    def log_error(self, msg):
        self.error_msg = msg
        self.gcode.respond_raw(f"!! {msg}")

    def save_variable(self, variable, value, write=False):
        self.save_variables.allVariables[variable] = value
        if write:
            self.write_variables()

    def rgb2hex(self, r, g, b):
        return "%02X%02X%02X" % (r, g, b)

    def delete_variable(self, variable, write=False):
        _ = self.save_variables.allVariables.pop(variable, None)
        if write:
            self.write_variables()

    def write_variables(self):
        mmu_vars_revision = self.save_variables.allVariables.get(self.VARS_ACE_REVISION, 0) + 1
        self.gcode.run_script_from_command(
            f"SAVE_VARIABLE VARIABLE={self.VARS_ACE_REVISION} VALUE={mmu_vars_revision}")

    def _get_next_request_id(self) -> int:
        self._request_id += 1
        if self._request_id >= 300000:
            self._request_id = 0
        return self._request_id

    def _serial_disconnect(self):
        self._connected = False
        self._reset_fast_origins()
        self._cancel_auto_preloads()
        self._rfid_sync = [None] * 4
        pending = self._clear_filament_query()
        if pending is not None:
            pending['complete'](None, 'disconnected')
        self._last_status_time = None
        self._heartbeat_request = None
        self.gate_status = [GATE_UNKNOWN] * 4
        self.read_buffer = bytearray()
        self._callback_map.clear()
        if self.heartbeat_timer is not None:
            self.reactor.unregister_timer(self.heartbeat_timer)
            self.heartbeat_timer = None
        if self.ace_dev_fd is not None:
            self.reactor.unregister_fd(self.ace_dev_fd)
            self.ace_dev_fd = None
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception as exc:
                self.log_error(f'ACE serial close failed: {exc}')
            self._serial = None

    def _transport_failed(self, message):
        self.log_error(message)
        self._serial_disconnect()
        if not self._shutting_down and self.connect_timer is None:
            self.connect_timer = self.reactor.register_timer(
                self._connect, self.reactor.monotonic() + 1.0)

    def _require_connected(self):
        if not self._connected or self._serial is None or not self._serial.is_open:
            raise AceException('ACE is disconnected; command aborted')

    def _validate_index(self, index):
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < 4:
            raise AceException(f'Invalid ACE channel: {index!r}')

    def _reset_fast_origins(self):
        self._fast_origins = [None] * 4
        self._takeup_ready = None
        self._gate_epochs = [epoch + 1 for epoch in self._gate_epochs]
        self._motion_pending.clear()

    def _invalidate_motion_origin(self, request):
        if request.get('method') not in ('feed_filament', 'unwind_filament',
                'start_feed_assist', 'stop_feed_assist', 'update_feeding_speed',
                'stop_feed_filament'):
            return
        index = request.get('params', {}).get('index')
        self._validate_index(index)
        self._takeup_ready = None
        self._fast_origins[index] = None
        self._motion_pending.add(index)

    def take_fast_origin(self, index):
        self._validate_index(index)
        origin = self._fast_origins[index]
        self._fast_origins[index] = None
        valid = bool(origin is not None and self.is_ace_ready()
                    and not self._control_inflight and not self._motion_pending
                    and self.gate_status[index] == GATE_AVAILABLE
                    and origin['connection'] == self._connected_at
                    and origin['gate_epoch'] == self._gate_epochs[index])
        if not valid:
            return None
        advance = origin.get('advance_upper_mm')
        if type(advance) is not int or not 0 <= advance <= 500:
            return None
        return dict(origin)

    def mark_unloaded(self, index, connection, gate_epoch, advance_upper_mm=0):
        # Caller additionally verifies that the U1 head sensor is now empty.
        self._validate_index(index)
        self._fast_origins[index] = None
        if type(advance_upper_mm) is not int or not 0 <= advance_upper_mm <= 500:
            raise AceException('Invalid forward-takeup position allowance')
        if (not self.is_ace_ready() or self._control_inflight or self._motion_pending
                or self._connected_at != connection
                or self._gate_epochs[index] != gate_epoch
                or self.gate_status[index] != GATE_AVAILABLE
                or self._feed_assist_index != -1):
            return False
        self._fast_origins[index] = {'reason': 'unloaded', 'connection': connection,
                                     'gate_epoch': gate_epoch, 'advance_upper_mm': advance_upper_mm}
        return True

    @staticmethod
    def _check_response(response):
        if not isinstance(response, dict):
            raise AceException('Malformed ACE response')
        if response.get('code', 0) != 0 or response.get('error'):
            raise AceException(f"ACE rejected command: {response.get('msg', response.get('error', response))}")
        message = response.get('msg')
        if message is not None and (not isinstance(message, str) or
                message.strip().lower() not in ('', 'success', 'ok')):
            raise AceException(f'ACE rejected command: {message}')

    def _connect(self, eventtime):
        if self._shutting_down:
            return self.reactor.NEVER

        def info_callback(self, response):
            self._check_response(response)
            result = response.get('result', {})
            model = result.get('model', 'Unknown')
            firmware = result.get('firmware', 'Unknown')
            self.log_always(f"{{2}}ACE: Connected to {model} {{0}} \n Firmware Version: {{3}}{firmware}{{0}}", True)

        try:
            self._serial = serial.Serial(
                port=self.serial_id,
                baudrate=self.baud,
                exclusive=True,
                rtscts=True,
                timeout=0,
                write_timeout=0)

            if self._serial.is_open:
                self._connected = True
                self._reset_fast_origins()
                self._cancel_auto_preloads()
                self.gate_status = [GATE_UNKNOWN] * 4
                self._rfid_sync = [None] * 4
                self._last_status_time = None
                self._connected_at = self.reactor.monotonic()
                self._request_id = 0
                logging.info(f'ACE: Connected to {self.serial_id}')
                self.ace_dev_fd = self.reactor.register_fd(
                    self._serial.fileno(),
                    self._reader_cb,
                )
                self.heartbeat_timer = self.reactor.register_timer(self._periodic_heartbeat_event, self.reactor.NOW)
                self.send_request(request={"method": "get_info"}, callback=info_callback,
                                  mark_busy=False)
                # Reconnection must not resume physical feeding automatically.
                if self.connect_timer is not None:
                    self.reactor.unregister_timer(self.connect_timer)
                    self.connect_timer = None
                return self.reactor.NEVER
        except serial.serialutil.SerialException:
            self._serial_disconnect()
            logging.info('ACE: Conn error')
            self.log_error(f'Error connecting to {self.serial_id}')
        except Exception as e:
            self.log_error(f"ACE Error: {e}")
            self._serial_disconnect()

        return eventtime + 1

    def _calc_crc(self, buffer):
        _crc = 0xFFFF
        for byte in buffer:
            data = byte
            data ^= _crc & 0xFF
            data ^= (data & 0x0F) << 4
            _crc = ((data << 8) | (_crc >> 8)) ^ (data >> 4) ^ (data << 3)
        return _crc

    def _send_request(self, request):
        self._require_connected()
        if 'id' not in request:
            request['id'] = self._get_next_request_id()

        payload = json.dumps(request).encode('utf-8')
        if len(payload) > 1024:
            raise AceException(f'ACE payload too large ({len(payload)} bytes)')

        crc = self._calc_crc(payload)
        # Re-generate payload if CRC matches sync bytes 0xFFAA to prevent freezing
        # as suggested by protocol description.
        attempts = 0
        while crc == 0xAAFF and attempts < 10:
            old_id = request['id']
            request['id'] = self._get_next_request_id()
            if old_id in self._callback_map:
                self._callback_map[request['id']] = self._callback_map.pop(old_id)
            payload = json.dumps(request).encode('utf-8')
            crc = self._calc_crc(payload)
            attempts += 1
        if crc == 0xAAFF:
            raise AceException('Unable to encode ACE request safely')

        data = bytes([0xFF, 0xAA])
        data += struct.pack('<H', len(payload))
        data += payload
        data += struct.pack('<H', crc)
        data += bytes([0xFE])
        try:
            written = self._serial.write(data)
            if written != len(data):
                raise AceException(f'Incomplete serial write: {written}/{len(data)} bytes')
        except Exception as exc:
            self._transport_failed(f'ACE serial write failed: {exc}')
            raise AceException(f'ACE serial write failed: {exc}') from exc

    def _pre_load(self, gate):
        # Insertion permits native ACE bite/NFC only. Long transport belongs to
        # the explicit U1 Load operation, which stops on the head-side sensor.
        # Keep this entry point non-moving even if an old caller invokes it.
        if self._connected:
            self.log_always('ACE filament inserted INDEX=%d; select Load on U1' % gate)

    def _cancel_auto_preloads(self):
        self._preload_generation += 1
        self._preload_jobs.clear()
        self._preload_queue.clear()
        self._preload_worker = None

    def _preload_job_valid(self, job, after_send=False):
        return (self._connected and job['generation'] == self._preload_generation and
                self._preload_jobs.get(job['index']) is job and
                (after_send or (not job['insertion_changed'] and
                                self.gate_status[job['index']] == GATE_AVAILABLE)))

    def _ensure_preload_worker(self):
        if not self._connected or self._preload_worker is not None or not self._preload_queue:
            return
        worker = object()
        self._preload_worker = worker
        self.reactor.register_async_callback(lambda et: self._run_preload_worker(worker))

    def _wait_preload_ready(self, job, deadline, after_send=False):
        while self._preload_job_valid(job, after_send=after_send):
            now = self.reactor.monotonic()
            if now >= deadline:
                raise AceException('automatic preload wait timed out')
            if self.is_ace_ready() and not self._control_inflight:
                return True
            self.reactor.pause(min(deadline, now + 0.1))
        return False

    def _run_preload_worker(self, worker):
        job = None
        try:
            while self._preload_worker is worker and self._connected and self._preload_queue:
                job = self._preload_queue.pop(0)
                if not self._preload_job_valid(job):
                    continue
                index = job['index']
                self.log_always('Wait ACE preload INDEX=%d' % index)
                if not self._wait_preload_ready(job, job['deadline']):
                    continue
                job['phase'] = 'sending'
                self._feed(index, self.feed_length, self.feed_speed, 0, _preload_token=job)
                job['phase'] = 'finishing'
                # Starting near the NFC deadline still receives a full completion window.
                finish_deadline = self.reactor.monotonic() + self.feed_length / self.feed_speed + self.READY_TIMEOUT
                if self._wait_preload_ready(job, finish_deadline, after_send=True):
                    if job['insertion_changed']:
                        self.log_always('ACE preload INDEX=%d ended after insertion changed; no automatic retry' % index)
                    else:
                        self.log_always('ACE preload complete INDEX=%d; Select AutoLoad from the menu' % index)
                    if self._preload_jobs.get(index) is job:
                        self._preload_jobs.pop(index)
        except Exception as exc:
            status = self.get_status()
            self.log_error('ACE preload failed INDEX=%s phase=%s status=%s fresh=%s: %s' % (
                job['index'] if job else '?', job['phase'] if job else '?',
                status['status'], status['status_fresh'], exc))
            # A cancelled old worker must not clear a newer connection/worker's jobs.
            if self._preload_worker is worker:
                self._cancel_auto_preloads()
        finally:
            if self._preload_worker is worker:
                self._preload_worker = None
                self._ensure_preload_worker()

    def _run_background(self, action, label):
        try:
            action()
        except Exception as exc:
            self.log_error(f'ACE {label} failed: {exc}')

    def _clear_filament_query(self):
        pending = self._filament_query
        self._filament_query = None
        if pending is not None:
            self._callback_map.pop(pending['id'], None)
            if pending['timer'] is not None:
                self.reactor.unregister_timer(pending['timer'])
        return pending

    cmd_ACE_QUERY_FILAMENT_help = 'Read cached ACE material metadata for INDEX=0..3; no motion'

    @ace_gcode_command
    def cmd_ACE_QUERY_FILAMENT(self, gcmd):
        index = gcmd.get_int('INDEX')
        def report(info, error):
            if error is not None:
                self.gcode.respond_info('ACE_QUERY_FILAMENT INDEX=%d failed: %s' % (index, error))
            else:
                self.gcode.respond_info('ACE_QUERY_FILAMENT ' + json.dumps(info, ensure_ascii=True, sort_keys=True))
        self._request_filament_info(index, report)

    def _request_filament_info(self, index, complete, strict=False):
        self._validate_index(index)
        self._require_connected()
        if self._control_inflight:
            raise AceException('ACE control command in progress; retry the query later')
        if self._filament_query is not None:
            raise AceException('ACE filament query already in progress')
        pending = {'index': index, 'id': None, 'timer': None, 'complete': complete}
        self._filament_query = pending

        def timeout(eventtime):
            if self._filament_query is pending:
                self._clear_filament_query()
                complete(None, 'response timed out')
            return self.reactor.NEVER

        def callback(self, response):
            if self._filament_query is not pending:
                return
            self._clear_filament_query()
            try:
                self._check_response(response)
                result = response.get('result')
                if not isinstance(result, dict):
                    raise AceException('Invalid result')
                if strict and any(key not in result for key in ('index', 'sku', 'brand', 'type', 'rfid', 'color')):
                    raise AceException('Incomplete material details')
                if 'index' in result and (type(result['index']) is not int or result['index'] != index):
                    raise AceException('Mismatched channel')
                info = {'index': index}
                for key in ('sku', 'brand', 'type'):
                    if key in result:
                        if not isinstance(result[key], str):
                            raise AceException('Invalid text field')
                        info[key] = result[key]
                if 'rfid' in result:
                    if type(result['rfid']) is not int:
                        raise AceException('Invalid RFID state')
                    info['rfid'] = result['rfid']
                if 'color' in result:
                    color = result['color']
                    if (not isinstance(color, list) or len(color) != 3 or
                            any(type(c) is not int or not 0 <= c <= 255 for c in color)):
                        raise AceException('Invalid color')
                    info['color'] = color
            except Exception:
                # Do not echo arbitrary response fields, UID data, or device errors.
                complete(None, 'invalid or rejected response')
                return
            complete(info, None)

        try:
            pending['id'] = self.send_request(
                {'method': 'get_filament_info', 'params': {'index': index}},
                callback, mark_busy=False)
            pending['timer'] = self.reactor.register_timer(
                timeout, self.reactor.monotonic() + self.REQUEST_TIMEOUT)
        except Exception:
            self._clear_filament_query()
            raise

    @staticmethod
    def _rfid_fingerprint(spool):
        if not isinstance(spool, dict) or type(spool.get('rfid')) is not int or spool['rfid'] != 2:
            return None
        if not isinstance(spool.get('sku'), str) or not isinstance(spool.get('type'), str) or not spool['type'].strip():
            return None
        color = spool.get('color')
        if (not isinstance(color, (list, tuple)) or len(color) != 3 or
                any(type(c) is not int or not 0 <= c <= 255 for c in color)):
            return None
        brand = spool.get('brand')
        if brand is not None and not isinstance(brand, str):
            return None
        if brand is not None:
            brand = brand.strip() or None
        return (spool['sku'], spool['type'], tuple(color), brand)

    def _rfid_sync_current(self, index, state):
        return (self._connected and self._rfid_sync[index] is state and
                self.gate_status[index] == GATE_AVAILABLE and
                self._last_status_time is not None and
                self._last_status_epoch == self._status_epoch and
                self.reactor.monotonic() - self._last_status_time <= self.STATUS_TIMEOUT and
                self._rfid_fingerprint(self._info['slots'][index]) == state['fingerprint'])

    def _consider_rfid_sync(self, index, spool):
        if self.gate_status[index] != GATE_AVAILABLE:
            # Empty-slot firmware caches must not resurrect removed material.
            # A fresh insertion, even of the same tag, must synchronize again.
            self._rfid_sync[index] = None
            return
        fingerprint = self._rfid_fingerprint(spool)
        if ('index' in spool and (type(spool['index']) is not int or spool['index'] != index)):
            fingerprint = None
        state = self._rfid_sync[index]
        if fingerprint is None:
            self._rfid_sync[index] = None
            return
        if state is None or state['fingerprint'] != fingerprint:
            state = {'fingerprint': fingerprint, 'attempts': 0, 'next_try': 0.,
                     'pending': False, 'complete': False, 'last_error': None}
            self._rfid_sync[index] = state
        if (not state['complete'] and not state['pending'] and
                state['attempts'] < self.RFID_SYNC_ATTEMPTS and
                self.reactor.monotonic() >= state['next_try']):
            state['pending'] = True
            self.reactor.register_async_callback(lambda et: self._start_rfid_sync(index, state))

    def _rfid_sync_failed(self, index, state, error):
        if self._rfid_sync[index] is not state:
            return
        state['pending'] = False
        state['next_try'] = self.reactor.monotonic() + self.RFID_RETRY_DELAY
        state['last_error'] = error
        self.log_error('ACE RFID sync INDEX=%d attempt %d/%d failed: %s' %
                       (index, state['attempts'], self.RFID_SYNC_ATTEMPTS, error))

    def _defer_rfid_sync(self, index, state):
        state['pending'] = False
        if self._rfid_sync[index] is state:
            # Control/status changes postpone a valid query; they are not failures.
            state['attempts'] = max(0, state['attempts'] - 1)
            state['next_try'] = self.reactor.monotonic() + 1.

    def _start_rfid_sync(self, index, state):
        if not self._rfid_sync_current(index, state):
            state['pending'] = False
            return
        if self._control_inflight or self._filament_query is not None:
            state['pending'] = False
            state['next_try'] = self.reactor.monotonic() + 1.
            return
        state['attempts'] += 1

        def details(info, error):
            if self._rfid_sync[index] is not state:
                state['pending'] = False
                return
            fingerprint = self._rfid_fingerprint(info)
            expected = state['fingerprint']
            if (error is not None or fingerprint is None or info.get('index') != index or
                    fingerprint[:3] != expected[:3] or
                    (expected[3] is not None and fingerprint[3] != expected[3])):
                self._rfid_sync_failed(index, state, error or 'material details changed or are incomplete')
                return
            if not self._rfid_sync_current(index, state):
                self._defer_rfid_sync(index, state)
                return
            self.reactor.register_async_callback(lambda et: self._apply_rfid_sync(index, state, info))

        try:
            self._request_filament_info(index, details, strict=True)
        except Exception:
            self._rfid_sync_failed(index, state, 'material query could not be sent')

    def _apply_rfid_sync(self, index, state, info):
        if not self._rfid_sync_current(index, state):
            self._defer_rfid_sync(index, state)
            return
        if self._control_inflight:
            self._defer_rfid_sync(index, state)
            return
        try:
            self._update_rfid(index, info)
        except Exception as exc:
            # Preserve U1 official-filament/Spoolman guards; never FORCE an update.
            self._rfid_sync_failed(index, state, str(exc))
            return
        state['pending'] = False
        state['complete'] = True
        state['last_error'] = None

    @staticmethod
    def _filament_brand(brand):
        brand = brand.strip()
        aliases = {'bambu lab': 'Bambu', 'bambulab': 'Bambu', 'bambu': 'Bambu',
                   'creality': 'Creality', 'elegoo': 'Elegoo', 'qidi': 'QIDI',
                   'snapmaker': 'Snapmaker', 'anycubic': 'Anycubic'}
        return aliases.get(brand.casefold(), brand) if brand else 'Generic'

    def _update_rfid(self, index, spool):
        # RFID text is data, never additional G-code or quoted parameters.
        def field(value):
            return str(value).replace('"', '').replace('\r', ' ').replace('\n', ' ')
        color = spool.get('color', (0, 0, 0))
        if len(color) != 3 or any(not isinstance(c, int) or not 0 <= c <= 255 for c in color):
            raise AceException('Invalid RFID color')
        material = spool.get('type', '').strip()
        if not material:
            raise AceException('Empty RFID material type')
        main_type, separator, subtype = material.partition(' ')
        if not separator or main_type not in self.MATERIAL_BASE_TYPES:
            main_type, subtype = material, ''
        brand = self._filament_brand(spool.get('brand', ''))
        self.gcode.run_script_from_command(
            f'SET_PRINT_FILAMENT_CONFIG CONFIG_EXTRUDER={index} '
            f'FILAMENT_TYPE="{field(main_type)}" '
            f'FILAMENT_COLOR_RGBA={self.rgb2hex(*color)} '
            f'VENDOR="{field(brand)}" FILAMENT_SUBTYPE="{field(subtype.strip())}"')

    def _periodic_heartbeat_event(self, eventtime):
        status_epoch = self._status_epoch
        def callback(self, response):
            self._heartbeat_request = None
            self._check_response(response)
            # A status request sent before a control command cannot prove that
            # command has finished, even if its reply arrives after the ACK.
            if status_epoch != self._status_epoch:
                return
            result = response.get('result', {})
            slots = result.get('slots', [])
            if len(slots) != 4 or 'status' not in result:
                raise AceException('Incomplete ACE status response')
            old_gates = self.gate_status[:]
            insertion_allowed = (getattr(self, '_u1_load_owner', None) is None
                                 and not self._u1_unload_depth
                                 and not self._motion_pending
                                 and not self._control_inflight
                                 and self._feed_assist_index == -1)
            self._info.update(result)
            self._last_status_time = self.reactor.monotonic()
            self._last_status_epoch = status_epoch
            self.error_msg = None
            for i in range(4):
                self.gate_status[i] = GATE_EMPTY if slots[i].get('status') == 'empty' else GATE_AVAILABLE
                if old_gates[i] != self.gate_status[i]:
                    self._fast_origins[i] = None
                    self._gate_epochs[i] += 1
                if self.gate_status[i] == GATE_EMPTY:
                    job = self._preload_jobs.get(i)
                    if job is not None and job['sent']:
                        # Keep the slot occupied until this send settles; an ABA
                        # sensor edge during motion must not queue another full feed.
                        job['insertion_changed'] = True
                    else:
                        self._preload_jobs.pop(i, None)
                # Unknown -> loaded on startup/reconnect must never feed.
                if old_gates[i] == GATE_EMPTY and self.gate_status[i] == GATE_AVAILABLE:
                    if insertion_allowed:
                        self._fast_origins[i] = {'reason': 'inserted',
                            'connection': self._connected_at, 'gate_epoch': self._gate_epochs[i],
                            'advance_upper_mm': 0}
                    self._pre_load(i)
                if old_gates[i] != self.gate_status[i]:
                    try:
                        self.printer.send_event('ace:gate_changed', i,
                                                self.gate_status[i] == GATE_AVAILABLE)
                    except Exception as exc:
                        logging.warning('ACE gate UI notification failed: %s', exc)
                self._consider_rfid_sync(i, slots[i])
            if result['status'] == 'ready' and not self._control_inflight:
                self._motion_pending.clear()
        if not self._connected:
            return self.reactor.NEVER
        last = self._last_status_time if self._last_status_time is not None else self._connected_at
        if last is not None and eventtime - last > self.STATUS_TIMEOUT:
            self._transport_failed('ACE status timed out; controls aborted')
            return self.reactor.NEVER
        if self._heartbeat_request is not None:
            request_id, sent_at = self._heartbeat_request
            if eventtime - sent_at > self.REQUEST_TIMEOUT:
                self._callback_map.pop(request_id, None)
                self._transport_failed('ACE heartbeat response timed out')
                return self.reactor.NEVER
            return eventtime + 1
        try:
            request_id = self.send_request({'method': 'get_status'}, callback, mark_busy=False)
            self._heartbeat_request = (request_id, eventtime)
        except AceException:
            return self.reactor.NEVER
        return eventtime + 1

    def _reader_cb(self, eventtime):
        try:
            if self._serial.in_waiting:
                raw_bytes = self._serial.read(size=self._serial.in_waiting)
                self._process_data(raw_bytes)
        except Exception as exc:
            logging.info(f'ACE error reading/processing: {traceback.format_exc()}')
            self._transport_failed(f'Unable to communicate with ACE: {exc}')

    def _process_data(self, raw_bytes):
        self.read_buffer += raw_bytes
        while len(self.read_buffer) >= 7:
            # Find sync bytes
            start = self.read_buffer.find(b'\xFF\xAA')
            if start < 0:
                # No sync bytes found, but we might have partial sync at the end
                if self.read_buffer.endswith(b'\xFF'):
                    self.read_buffer = self.read_buffer[-1:]
                else:
                    self.read_buffer = bytearray()
                break

            if start > 0:
                self.read_buffer = self.read_buffer[start:]

            if len(self.read_buffer) < 4:
                break

            payload_len = struct.unpack('<H', self.read_buffer[2:4])[0]
            if payload_len > 2048:  # Sanity check: protocol says max 1024, but allow some headroom
                self.gcode.respond_info(f"ACE: Invalid payload length {payload_len}, dropping sync bytes")
                self.read_buffer = self.read_buffer[2:]
                continue

            total_len = 4 + payload_len + 2 + 1  # head + payload + crc + tail

            if len(self.read_buffer) < total_len:
                break

            packet = self.read_buffer[:total_len]
            payload = packet[4:4 + payload_len]
            crc_data = packet[4 + payload_len:4 + payload_len + 2]
            tail = packet[-1]

            # if tail != 0xFE:
            #     self.gcode.respond_info(f"Invalid tail byte from ACE: {tail:02X}, dropping sync bytes")
            #     self.read_buffer = self.read_buffer[2:]  # Drop current sync bytes and continue searching
            #     continue
            #
            # calc_crc = struct.pack('<H', self._calc_crc(payload))
            # if crc_data != calc_crc:
            #     self.gcode.respond_info('Invalid CRC from ACE PRO, dropping sync bytes')
            #     self.read_buffer = self.read_buffer[2:]  # Drop current sync bytes and continue searching
            #     continue

            # Packet is valid, consume it from buffer
            self.read_buffer = self.read_buffer[total_len:]

            try:
                ret = json.loads(payload.decode('utf-8'))
            except (json.decoder.JSONDecodeError, UnicodeDecodeError):
                self.log_error('Invalid JSON/UTF-8 from ACE PRO')
                continue

            msg_id = ret.get('id')
            if msg_id in self._callback_map:
                callback = self._callback_map.pop(msg_id)
                try:
                    callback(self=self, response=ret)
                except Exception as exc:
                    self.log_error(f'ACE response handler failed: {exc}')

    def send_request(self, request, callback, mark_busy=True):
        self._require_connected()
        if mark_busy:
            self._info['status'] = 'busy'
            self._status_epoch += 1
        msg_id = self._get_next_request_id()
        self._callback_map[msg_id] = callback
        request['id'] = msg_id
        try:
            self._send_request(request)
        except Exception:
            self._callback_map.pop(request['id'], None)
            raise
        return request['id']

    def _command(self, request, ready=True, _poll=None):
        # Invalidate before attempting, including rejected/unsent operations.
        self._invalidate_motion_origin(request)
        if self._control_inflight:
            raise AceException('Another ACE control command is in progress')
        self._control_inflight = True
        request_id = None
        attempted = False
        try:
            if ready:
                self.wait_ace_ready()
            replies = []
            def callback(self, response):
                replies.append(response)
            self._invalidate_motion_origin(request)
            attempted = True
            request_id = self.send_request(request, callback)
            deadline = self.reactor.monotonic() + self.REQUEST_TIMEOUT
            while not replies:
                self._require_connected()
                if _poll is not None:
                    _poll()
                if self.reactor.monotonic() >= deadline:
                    raise AceException(f"ACE {request['method']} acknowledgement timed out")
                self.reactor.pause(self.reactor.monotonic() + 0.05)
            self._check_response(replies[0])
            if _poll is not None:
                _poll()
            return replies[0]
        except AceException as exc:
            exc.command_sent = attempted
            raise
        finally:
            if request_id is not None:
                self._callback_map.pop(request_id, None)
            self._control_inflight = False

    def wait_ace_ready(self, timeout=None):
        deadline = self.reactor.monotonic() + (self.READY_TIMEOUT if timeout is None else timeout)
        while True:
            self._require_connected()
            now = self.reactor.monotonic()
            if self._last_status_time is not None and now - self._last_status_time > self.STATUS_TIMEOUT:
                raise AceException('ACE status is stale; command aborted')
            if self.is_ace_ready():
                return
            if now >= deadline:
                raise AceException('ACE ready wait timed out')
            self.reactor.pause(now + 0.1)

    def is_ace_ready(self):
        return (self._connected and self._last_status_time is not None
                and self._last_status_epoch == self._status_epoch
                and self.reactor.monotonic() - self._last_status_time <= self.STATUS_TIMEOUT
                and self._info['status'] == 'ready')

    def dwell(self, delay=1.0):
        deadline = self.reactor.monotonic() + delay
        while self.reactor.monotonic() < deadline:
            self._require_connected()
            self.reactor.pause(min(deadline, self.reactor.monotonic() + 0.1))

    def _extruder_move(self, length, speed):
        pos = self.toolhead.get_position()
        pos[3] += length
        self.toolhead.move(pos, speed)
        return pos[3]

    cmd_ACE_START_DRYING_help = 'Starts ACE Pro dryer'

    @ace_gcode_command
    def cmd_ACE_START_DRYING(self, gcmd):
        temperature = gcmd.get_int('TEMP')
        duration = gcmd.get_int('DURATION', 240)

        if duration <= 0:
            raise gcmd.error('Wrong duration')
        if temperature <= 0 or temperature > self.max_dryer_temperature:
            raise gcmd.error('Wrong temperature')

        self._command({"method": "drying", "params": {
            "temp": temperature, "fan_speed": 7000, "duration": duration}})
        self.gcode.respond_info('Started ACE drying')

    cmd_ACE_STOP_DRYING_help = 'Stops ACE Pro dryer'

    @ace_gcode_command
    def cmd_ACE_STOP_DRYING(self, gcmd):
        self._command({"method": "drying_stop"}, ready=False)
        self.gcode.respond_info('Stopped ACE drying')

    def _enable_feed_assist(self, index):
        self._validate_index(index)
        owner = getattr(self, '_u1_load_owner', None)
        if owner is not None and owner.get('kind') == 'unload':
            self.log_always('ACE assist deferred until U1 unload completes INDEX=%d' % index)
            return
        if (owner is not None and self._connected
                and owner.get('connection') == self._connected_at
                and owner.get('index') == index and owner.get('allow_assist') is False):
            self.log_always('ACE assist deferred until U1 sensor load finishes INDEX=%d' % index)
            return
        self._require_connected()
        connected_at = self._connected_at
        def require_same_connection():
            if not self._connected or self._connected_at != connected_at:
                raise AceException('ACE connection changed during assist start; result unknown')
        self._invalidate_motion_origin({'method': 'start_feed_assist', 'params': {'index': index}})
        self._cancel_auto_preloads()
        # Establish readiness before the legacy retract's own immediate check;
        # it must not wait across reconnection and send to the new transport.
        self.wait_ace_ready()
        require_same_connection()
        if self._feed_assist_index != -1:
            self._validate_index(self._feed_assist_index)
            self._retract(self._feed_assist_index, 5, 10)
            require_same_connection()
        self.wait_ace_ready()
        require_same_connection()
        acknowledged = False
        try:
            self._command({"method": "start_feed_assist", "params": {"index": index}}, ready=False)
            require_same_connection()
            acknowledged = True
            self._feed_assist_index = index
            self.dwell(delay=0.7)
            require_same_connection()
        except Exception as exc:
            if not acknowledged and isinstance(exc, AceException) and not exc.command_sent:
                raise
            # A missing ACK can still mean the device accepted the start.
            # An obsolete attempt cannot stop or overwrite a new connection.
            if self._connected and self._connected_at == connected_at:
                self._feed_assist_index = index
                try:
                    self._command({"method": "stop_feed_assist", "params": {"index": index}}, ready=False)
                    require_same_connection()
                    self._feed_assist_index = -1
                except Exception as cleanup:
                    self.log_error(f'ACE assist cleanup also failed: {cleanup}')
            raise

    cmd_ACE_ENABLE_FEED_ASSIST_help = 'Enables ACE feed assist'

    @ace_gcode_command
    def cmd_ACE_ENABLE_FEED_ASSIST(self, gcmd):
        index = gcmd.get_int('INDEX')

        if index < 0 or index >= 4:
            raise gcmd.error('Wrong index')

        self._enable_feed_assist(index)

    def _disable_feed_assist(self, index=-1):
        self._require_connected()
        if index != -1:
            self._validate_index(index)
        self._cancel_auto_preloads()
        # The toolchange caller passes its target; the tracked active channel
        # is the one to stop/retract. Initial -1 means no assist was started.
        rt_index = self._feed_assist_index
        if rt_index == -1:
            return
        self._validate_index(rt_index)
        self._command({"method": "stop_feed_assist", "params": {"index": rt_index}}, ready=False)
        self._feed_assist_index = -1
        self.gcode.respond_info('Disabled ACE feed assist')
        self._retract(rt_index, 5, 10)
        self.dwell(0.3)

    def _stop_feed_assist_only(self):
        # U1's explicit load/unload owns the transfer distance. Stop assistance
        # without the legacy tool-change helper's additional 5 mm unwind.
        self._require_connected()
        self._cancel_auto_preloads()
        index = self._feed_assist_index
        if index == -1:
            return
        self._validate_index(index)
        connected_at = self._connected_at
        self._command({'method': 'stop_feed_assist', 'params': {'index': index}}, ready=False)
        if not self._connected or self._connected_at != connected_at:
            raise AceException('ACE connection changed while stopping assist; result unknown')
        self.wait_ace_ready()
        if not self._connected or self._connected_at != connected_at:
            raise AceException('ACE connection changed while stopping assist; result unknown')
        # Retain tracking after rejection, missing ACK, or completion timeout.
        self._feed_assist_index = -1
        self.gcode.respond_info('Stopped ACE feed assist without retract')

    cmd_ACE_DISABLE_FEED_ASSIST_help = 'Disables ACE feed assist'

    @ace_gcode_command
    def cmd_ACE_DISABLE_FEED_ASSIST(self, gcmd):
        index = gcmd.get_int('INDEX', self._feed_assist_index)

        if index < -1 or index >= 4:
            raise gcmd.error('Wrong index')

        self._disable_feed_assist(index)

    def _feed(self, index, length, speed, how_wait=None, _preload_token=None, _poll=None,
              _owner_token=None):
        self._validate_index(index)
        if length <= 0 or speed <= 0:
            raise AceException('ACE feed length/speed must be positive')
        if _preload_token is None:
            self._cancel_auto_preloads()
        elif not self._preload_job_valid(_preload_token) or _preload_token['index'] != index or _preload_token['sent']:
            raise AceException('Automatic preload was cancelled or already sent')
        self._require_connected()
        connected_at = self._connected_at
        self._invalidate_motion_origin({'method': 'feed_filament', 'params': {'index': index}})
        self.wait_ace_ready()
        if not self._connected or self._connected_at != connected_at:
            raise AceException('ACE connection changed before feed; command aborted')
        if _owner_token is not None and getattr(self, '_u1_load_owner', None) is not _owner_token:
            raise AceException('ACE operation owner changed before feed; command aborted')
        acknowledged = False
        try:
            if _preload_token is not None:
                if not self._preload_job_valid(_preload_token) or self._control_inflight:
                    raise AceException('Automatic preload was cancelled before send')
                _preload_token['sent'] = True
            self._command({"method": "feed_filament", "params": {
                "index": index, "length": length, "speed": speed}}, ready=False, _poll=_poll)
            if not self._connected or self._connected_at != connected_at:
                raise AceException('ACE connection changed during feed; result unknown')
            acknowledged = True
            distance = length if how_wait is None else how_wait
            if _poll is None:
                self.dwell(delay=(distance / speed) + 0.1)
            else:
                deadline = self.reactor.monotonic() + (distance / speed) + 0.1
                while self.reactor.monotonic() < deadline:
                    self._require_connected()
                    _poll()
                    self.reactor.pause(min(deadline, self.reactor.monotonic() + 0.05))
                _poll()
            if not self._connected or self._connected_at != connected_at:
                raise AceException('ACE connection changed during feed; result unknown')
        except Exception as exc:
            if not acknowledged and isinstance(exc, AceException) and not exc.command_sent:
                raise
            if _preload_token is not None and not self._preload_job_valid(_preload_token, after_send=True):
                # An obsolete automatic task must not stop a newer connection or
                # a manual operation that superseded it while its ACK was pending.
                raise
            if (self._connected and self._connected_at == connected_at
                    and (_owner_token is None or
                         (getattr(self, '_u1_load_owner', None) is _owner_token
                          and (self._gate_epochs[index] == _owner_token['gate_epoch']
                               or self.gate_status[index] == GATE_EMPTY)))):
                try:
                    self._stop_feeding(index)
                    if self._connected and self._connected_at == connected_at:
                        exc._ace_feed_stop_confirmed = True
                except Exception as cleanup:
                    self.log_error(f'ACE feed cleanup also failed: {cleanup}')
            raise

    cmd_ACE_FEED_help = 'Feeds filament from ACE'

    @ace_gcode_command
    def cmd_ACE_FEED(self, gcmd):
        index = gcmd.get_int('INDEX')
        length = gcmd.get_int('LENGTH')
        speed = gcmd.get_int('SPEED', self.feed_speed)

        if index < 0 or index >= 4:
            raise gcmd.error('Wrong index')
        if length <= 0:
            raise gcmd.error('Wrong length')
        if speed <= 0:
            raise gcmd.error('Wrong speed')

        self._feed(index, length, speed)

    def _retract(self, index, length, speed, _poll=None):
        self._validate_index(index)
        if length <= 0 or speed <= 0:
            raise AceException('ACE retract length/speed must be positive')
        self._cancel_auto_preloads()
        self._command({"method": "unwind_filament", "params": {
            "index": index, "length": length, "speed": speed}}, _poll=_poll)
        if _poll is None:
            self.dwell(delay=(length / speed) + 0.1)
        else:
            until = self.reactor.monotonic() + length / speed + 0.1
            while self.reactor.monotonic() < until:
                _poll()
                self.reactor.pause(min(until, self.reactor.monotonic() + 0.05))
            _poll()

    def retract_fil(self, index):
        self._require_connected()
        self._validate_index(index)
        connected_at = self._connected_at
        gate_epoch = self._gate_epochs[index]
        owner = getattr(self, '_u1_load_owner', None)
        self._takeup_ready = None
        self._u1_unload_depth += 1
        try:
            self.wait_ace_ready()
            if not self._connected or self._connected_at != connected_at:
                raise AceException('ACE connection changed before retract; command aborted')
            if self.forward_takeup_length > 0:
                # A failed selector can report ready without executing length.
                # Tail eligibility therefore needs actual same-epoch unwinding.
                initial_epoch = self._status_epoch
                deadline = (self.reactor.monotonic() + self.retract_length / self.retract_speed
                            + self.READY_TIMEOUT)
                next_heartbeat, saw_unwinding = self.reactor.monotonic(), False

                def poll():
                    nonlocal next_heartbeat, saw_unwinding
                    if (not self._connected or self._shutting_down or self._connected_at != connected_at
                            or getattr(self, '_u1_load_owner', None) is not owner
                            or self._gate_epochs[index] != gate_epoch
                            or self.gate_status[index] != GATE_AVAILABLE
                            or (owner is not None and owner.get('cancelled', False))):
                        raise AceException('ACE retract interrupted; no forward takeup or retry')
                    now = self.reactor.monotonic()
                    if now >= deadline:
                        raise AceException('ACE retract did not prove unwinding completion; no forward takeup')
                    if now >= next_heartbeat and self._heartbeat_request is None:
                        next_heartbeat = now + 0.1
                        self._periodic_heartbeat_event(now)
                    status = self.get_status()
                    if not status['status_fresh'] or self._status_epoch <= initial_epoch:
                        return
                    slots = self._info['slots']
                    if status['status'] not in ('ready', 'busy') or len(slots) != 4:
                        raise AceException('ACE error during retract; no forward takeup')
                    for i, slot in enumerate(slots):
                        allowed = ('ready', 'empty', 'shifting', 'unwinding') if i == index else ('ready', 'empty')
                        if slot.get('status') not in allowed:
                            raise AceException('Unexpected ACE slot state during retract; no forward takeup')
                    if status['status'] == 'busy' and slots[index]['status'] == 'unwinding':
                        saw_unwinding = True

                poll()  # Ownership may have changed while the initial ready wait yielded.
                self._retract(index, self.retract_length, self.retract_speed, _poll=poll)
                while True:
                    poll()
                    if (saw_unwinding and self.is_ace_ready() and not self._control_inflight
                            and self._info['slots'][index]['status'] == 'ready'):
                        break
                    self.reactor.pause(min(deadline, self.reactor.monotonic()+0.05))
            else:
                self._retract(index, self.retract_length, self.retract_speed)
            if not self._connected or self._connected_at != connected_at:
                raise AceException('ACE connection changed during retract; result unknown')
            # ACK and distance dwell do not establish physical completion.
            self.wait_ace_ready()
            if not self._connected or self._connected_at != connected_at:
                raise AceException('ACE connection changed during retract; result unknown')
            if (self._gate_epochs[index] == gate_epoch and self.gate_status[index] == GATE_AVAILABLE
                    and getattr(self, '_u1_load_owner', None) is owner):
                self._takeup_ready = {'index': index, 'connection': connected_at,
                                      'gate_epoch': gate_epoch, 'owner': owner}
        finally:
            self._u1_unload_depth -= 1

    def forward_takeup(self, index, connection, gate_epoch, _poll=None, token=None):
        """One finite forward move after a completed normal retract; no retry.

        This draws slack into the tube, not independent roller winding or tension
        detection. The caller owns the unload and guards the U1 head sensor.
        """
        self._validate_index(index)
        receipt = self._takeup_ready
        self._takeup_ready = None
        if (token is None or receipt is None or receipt.get('owner') is not token
                or receipt.get('index') != index or receipt.get('connection') != connection
                or receipt.get('gate_epoch') != gate_epoch):
            raise AceException('Forward takeup requires one completed normal retract; no replay')
        if not callable(_poll):
            raise AceException('Forward takeup requires a U1 head/cancellation guard')

        def same_owner():
            return (self._connected and self._connected_at == connection
                    and getattr(self, '_u1_load_owner', None) is token
                    and self._gate_epochs[index] == gate_epoch)

        def can_clean_up():
            return (self._connected and self._connected_at == connection
                    and getattr(self, '_u1_load_owner', None) is token
                    and (self._gate_epochs[index] == gate_epoch or self.gate_status[index] == GATE_EMPTY))

        def guard():
            if (not same_owner() or self._shutting_down or token.get('kind') != 'unload'
                    or token.get('index') != index or token.get('connection') != connection
                    or token.get('gate_epoch') != gate_epoch or token.get('cancelled', False)
                    or self.gate_status[index] != GATE_AVAILABLE):
                raise AceException('Forward takeup interrupted; no automatic resend')
            _poll()

        guard()
        self._fast_origins[index] = None
        length, speed = self.forward_takeup_length, self.forward_takeup_speed
        if (type(length) is not int or not 0 <= length <= 500
                or length >= min(self.retract_length, self.FAST_LOAD_LENGTH)
                or type(speed) is not int or not 1 <= speed <= 50):
            raise AceException('Invalid forward-takeup configuration')
        if length == 0:
            return 0
        if not self.is_ace_ready() or self._control_inflight or self._feed_assist_index != -1:
            raise AceException('ACE is not ready for forward takeup')
        deadline = self.reactor.monotonic() + length / speed + self.READY_TIMEOUT
        next_heartbeat = self.reactor.monotonic()
        started = False
        saw_feeding = False

        def poll():
            nonlocal next_heartbeat, saw_feeding
            guard()
            now = self.reactor.monotonic()
            if now >= deadline:
                raise AceException('Forward takeup completion timed out; no automatic resend')
            if now >= next_heartbeat and self._heartbeat_request is None:
                next_heartbeat = now + 0.1
                self._periodic_heartbeat_event(now)
            status = self.get_status()
            if not status['status_fresh']:
                return
            slots = self._info['slots']
            if status['status'] not in ('ready', 'busy') or len(slots) != 4:
                raise AceException('ACE error during forward takeup')
            for i, slot in enumerate(slots):
                allowed = ('ready', 'empty', 'shifting', 'feeding') if i == index else ('ready', 'empty')
                if slot.get('status') not in allowed:
                    raise AceException('Unexpected ACE slot state during forward takeup')
            if started and status['status'] == 'busy' and slots[index]['status'] == 'feeding':
                saw_feeding = True

        try:
            poll()
            started = True
            self._feed(index, length, speed, 0, _poll=poll, _owner_token=token)
            while True:
                poll()
                if (saw_feeding and self.is_ace_ready() and not self._control_inflight
                        and self._info['slots'][index]['status'] == 'ready'):
                    guard()
                    return length
                self.reactor.pause(min(deadline, self.reactor.monotonic() + 0.05))
        except Exception as exc:
            if can_clean_up():
                self._fast_origins[index] = None
                if started:
                    try:
                        if not getattr(exc, '_ace_feed_stop_confirmed', False):
                            self._stop_feeding(index)
                        self.wait_ace_ready(timeout=self.SENSOR_LOAD_FINISH_TIMEOUT)
                    except Exception as cleanup:
                        self.log_error('Forward-takeup cleanup also failed: %s' % cleanup)
            raise

    cmd_ACE_RETRACT_help = 'Retracts filament back to ACE'

    @ace_gcode_command
    def cmd_ACE_RETRACT(self, gcmd):
        index = gcmd.get_int('INDEX')
        length = gcmd.get_int('LENGTH')
        speed = gcmd.get_int('SPEED', self.retract_speed)

        if index < 0 or index >= 4:
            raise gcmd.error('Wrong index')
        if length <= 0:
            raise gcmd.error('Wrong length')
        if speed <= 0:
            raise gcmd.error('Wrong speed')

        self._retract(index, length, speed)

    def _set_feeding_speed(self, index, speed):
        self._validate_index(index)
        if speed <= 0:
            raise AceException('ACE feed speed must be positive')
        self._cancel_auto_preloads()
        self._command({"method": "update_feeding_speed", "params": {
            "index": index, "speed": speed}}, ready=False)

    def _stop_feeding(self, index):
        self._validate_index(index)
        self._cancel_auto_preloads()
        self._command({"method": "stop_feed_filament", "params": {"index": index}}, ready=False)

    def get_status(self, eventtime=None):
        return {
            'port_version': self.PORT_VERSION,
            'load_policy': 'u1_sensor',
            'connected': self._connected,
            'status_fresh': (self._last_status_time is not None and
                self._last_status_epoch == self._status_epoch and
                self.reactor.monotonic() - self._last_status_time <= self.STATUS_TIMEOUT),
            'feed_assist_index': self._feed_assist_index,
            'last_error': self.error_msg,
            'status': self._info['status'],
            'temp': self._info['temp'],
            'dryer_status': self._info['dryer_status'],
            'gate_status': self.gate_status,
            'fast_origins': [None if origin is None else origin['reason']
                             for origin in self._fast_origins],
            'fast_origin_advance_mm': [None if origin is None else origin.get('advance_upper_mm')
                                     for origin in self._fast_origins],
            'forward_takeup_length': self.forward_takeup_length,
            'forward_takeup_speed': self.forward_takeup_speed,
            'preload_queue': [{'index': job['index'], 'phase': job['phase'],
                'sent': job['sent']} for job in self._preload_jobs.values()],
            'rfid_sync': [None if state is None else {
                'attempts': state['attempts'], 'pending': state['pending'],
                'complete': state['complete'], 'last_error': state['last_error']}
                for state in self._rfid_sync],
        }


def load_config(config):
    return BunnyAce(config)

