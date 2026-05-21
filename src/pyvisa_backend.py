from __future__ import annotations

import time
import random
from typing import List, Optional, Tuple

from .multi_func import Multimeter


# Profile for Agilent/Keysight 34401A
AGILENT_34401A_PROFILE = {
    'name': 'agilent_34401a',
    'id_contains': ['34401A', '34401'],
    'modes': {
        'VDC': {
            'conf': 'CONF:VOLT:DC {range}',
            'measure': 'MEAS:VOLT:DC?'
        },
        'VAC': {
            'conf': 'CONF:VOLT:AC {range}',
            'measure': 'MEAS:VOLT:AC?'
        },
        'A': {
            'conf': 'CONF:CURR:DC {range}',
            'measure': 'MEAS:CURR:DC?'
        },
        'OHM': {
            'conf': 'CONF:RES {range}',
            'measure': 'MEAS:RES?'
        },
        'HZ': {
            'measure': 'MEAS:FREQuency?'
        }
    },
    'supports_capacitance': False,
    'units': {
        'VDC': 'V', 'VAC': 'V', 'A': 'A', 'OHM': '\u03A9', 'HZ': 'Hz'
    }
}


class SimulatorMultimeter(Multimeter):
    def __init__(self) -> None:
        super().__init__()
        self.sim_base = {'VDC': 3.3, 'VAC': 5.0, 'A': 0.12, 'OHM': 1000.0, 'HZ': 60.0, 'CAP': 100e-9}
        self._running = False

    @staticmethod
    def list_resources() -> List[str]:
        return ['SIMULATE']

    def connect(self, resource: Optional[str] = None, *, simulate: bool = True, timeout_ms: Optional[int] = None) -> None:
        self.simulate = True
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def write(self, cmd: str) -> None:
        # no-op for simulator
        return

    def query(self, cmd: str, timeout_ms: Optional[int] = None) -> str:
        # return numeric string for queries
        v, _ = self.measure_raw()
        return f"{v:.6E}"

    def measure_raw(self) -> Tuple[float, str]:
        base = self.sim_base.get(self.mode, 1.0)
        # random small variation
        val = base + random.uniform(-0.01 * base, 0.01 * base)
        unit = {'VDC': 'V', 'VAC': 'V', 'A': 'A', 'OHM': '\u03A9', 'HZ': 'Hz', 'CAP': 'F'}.get(self.mode, '')
        time.sleep(0.01)
        return val, unit


class PyVISAMultimeter(Multimeter):
    def __init__(self) -> None:
        super().__init__()
        self._inst = None
        self._rm = None

    @staticmethod
    def list_resources() -> List[str]:
        try:
            import pyvisa
        except Exception:
            return []
        try:
            rm = pyvisa.ResourceManager()
        except Exception:
            try:
                rm = pyvisa.ResourceManager('@py')
            except Exception:
                return []
        try:
            return list(rm.list_resources())
        except Exception:
            return []

    def connect(self, resource: Optional[str] = None, *, simulate: bool = False, timeout_ms: Optional[int] = None) -> None:
        if simulate or (resource and resource.upper() == 'SIMULATE'):
            # fall back to simulator
            sim = SimulatorMultimeter()
            # copy config
            sim.calibration = self.calibration
            sim.averaging_enabled = self.averaging_enabled
            sim.averaging_count = self.averaging_count
            sim.profile = self.profile
            # replace self with sim behaviour via attributes
            self.__class__ = sim.__class__
            self.__dict__ = sim.__dict__
            return

        import pyvisa
        try:
            self._rm = pyvisa.ResourceManager()
        except Exception:
            self._rm = pyvisa.ResourceManager('@py')

        if not resource:
            resources = self._rm.list_resources()
            if not resources:
                raise RuntimeError('No VISA resources found')
            resource = resources[0]

        self._inst = self._rm.open_resource(resource)
        # reasonable defaults for serial-based XDM devices
        try:
            self._inst.baud_rate = 115200
            self._inst.data_bits = 8
            self._inst.stop_bits = pyvisa.constants.StopBits.one
            self._inst.parity = pyvisa.constants.Parity.none
        except Exception:
            pass
        try:
            self._inst.timeout = 3000
            self._inst.read_termination = '\n'
            self._inst.write_termination = '\n'
        except Exception:
            pass

        self.connected = True
        self.resource = resource

        # try to identify and select a device profile (e.g., Agilent 34401A)
        try:
            idn = self.query('*IDN?')
            self.idn = idn
            idn_upper = (idn or '').upper()
            # simple detection for 34401A
            for token in AGILENT_34401A_PROFILE['id_contains']:
                if token.upper() in idn_upper:
                    # attach profile and set profile name
                    self.instrument_profile = AGILENT_34401A_PROFILE
                    self.profile = AGILENT_34401A_PROFILE['name']
                    break
        except Exception:
            pass

    def disconnect(self) -> None:
        try:
            if self._inst:
                self._inst.close()
        except Exception:
            pass
        self._inst = None
        self.connected = False

    def write(self, cmd: str) -> None:
        if not self._inst:
            raise RuntimeError('Not connected')
        return self._inst.write(cmd)

    def query(self, cmd: str, timeout_ms: Optional[int] = None) -> str:
        if not self._inst:
            raise RuntimeError('Not connected')
        if timeout_ms is not None:
            self._inst.timeout = int(timeout_ms)
        return str(self._inst.query(cmd))

    def measure_raw(self) -> Tuple[float, str]:
        if not self._inst:
            raise RuntimeError('Not connected')

        # Try custom command for the mode
        cmd = self.custom_cmds.get(self.mode)
        if cmd:
            if '?' in cmd:
                resp = self.query(cmd)
                return float(self.parse_numeric_response(resp)), 'V'
            else:
                # config then measure
                if '{}' in cmd:
                    rng = 'AUTO' if (self.range is None or str(self.range).upper() == 'AUTO') else str(self.range)
                    self.write(cmd.format(rng))
                else:
                    self.write(cmd)
                # default MEAS1?
                resp = self.query('MEAS1?')
                return float(self.parse_numeric_response(resp)), 'V'

        # If a vendor profile is attached, use its commands
        prof = getattr(self, 'instrument_profile', None)
        if prof:
            mode_entry = prof.get('modes', {}).get(self.mode)
            if mode_entry:
                # optional configuration command
                conf = mode_entry.get('conf')
                if conf:
                    try:
                        if '{' in conf:
                            rng = 'AUTO' if (self.range is None or str(self.range).upper() == 'AUTO') else str(self.range)
                            # support both {range} and {} styles
                            if '{range}' in conf:
                                self.write(conf.format(range=rng))
                            else:
                                self.write(conf.format(rng))
                        else:
                            self.write(conf)
                    except Exception:
                        pass
                measure_cmd = mode_entry.get('measure')
                if measure_cmd:
                    resp = self.query(measure_cmd)
                    val = float(self.parse_numeric_response(resp))
                    unit = prof.get('units', {}).get(self.mode, '')
                    return val, unit

        # fallback mapping
        cmd_map = {
            'VDC': 'MEASure:VOLTage:DC?',
            'VAC': 'MEASure:VOLTage:AC?',
            'A': 'MEASure:CURRent:DC?',
            'OHM': 'MEASure:RESistance?',
            'HZ': 'MEASure:FREQuency?',
            'CAP': 'MEASure:CAPacitance?'
        }
        q = cmd_map.get(self.mode)
        if not q:
            raise RuntimeError('No query for mode')
        resp = self.query(q)
        val = float(self.parse_numeric_response(resp))
        unit_map = {'VDC': 'V', 'VAC': 'V', 'A': 'A', 'OHM': '\u03A9', 'HZ': 'Hz', 'CAP': 'F'}
        return val, unit_map.get(self.mode, '')
