"""Simple data logger for writing multimeter readings to JSONL files.

Usage:
  from src.data_logger import Logger
  lg = Logger(log_dir='logs')
  rec = lg.make_record(value=3.3, unit='V', instrument_id='OWON,XDM2041,123')
  lg.append(rec)
"""
import os
import json
import datetime
import uuid


class Logger:
    def __init__(self, log_dir='logs', prefix='measurements'):
        self.log_dir = log_dir
        self.prefix = prefix
        os.makedirs(self.log_dir, exist_ok=True)
        self.current_path = self._daily_path()

    def _daily_path(self):
        d = datetime.datetime.utcnow().strftime('%Y%m%d')
        return os.path.join(self.log_dir, f"{self.prefix}_{d}.jsonl")

    def rotate_if_needed(self):
        path = self._daily_path()
        if path != self.current_path:
            self.current_path = path

    def make_record(self, *, value, unit, instrument_id=None, mode=None, range=None,
                    averaging_count=None, calibration_offsets=None, raw_response=None,
                    sample_interval_s=None, session=None, note=None, tags=None, sequence=None):
        ts = datetime.datetime.utcnow().isoformat() + 'Z'
        rec = {
            'timestamp': ts,
            'measurement_id': str(uuid.uuid4()),
            'sequence': sequence,
            'instrument_id': instrument_id,
            'mode': mode,
            'range': range,
            'averaging_count': averaging_count,
            'calibration_offsets': calibration_offsets,
            'value': value,
            'unit': unit,
            'raw_response': raw_response,
            'sample_interval_s': sample_interval_s,
            'session': session,
            'note': note,
            'tags': tags or [],
        }
        # remove None values for compactness
        return {k: v for k, v in rec.items() if v is not None}

    def append(self, record, flush=True, fsync=False):
        """Append a JSON record to the current daily JSONL file."""
        self.rotate_if_needed()
        line = json.dumps(record, ensure_ascii=False)
        with open(self.current_path, 'a', encoding='utf-8') as fh:
            fh.write(line + '\n')
            if flush:
                fh.flush()
                if fsync:
                    os.fsync(fh.fileno())

    def read(self, path=None):
        path = path or self.current_path
        if not os.path.exists(path):
            return
        with open(path, 'r', encoding='utf-8') as fh:
            for line in fh:
                try:
                    yield json.loads(line)
                except Exception:
                    continue


def _quick_demo():
    lg = Logger(log_dir='logs_demo')
    rec = lg.make_record(value=1.2345, unit='V', instrument_id='SIMULATOR', mode='VDC', note='demo')
    lg.append(rec)
    print('Wrote to', lg.current_path)


if __name__ == '__main__':
    _quick_demo()
