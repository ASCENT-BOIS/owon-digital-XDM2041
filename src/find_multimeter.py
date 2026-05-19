#!/usr/bin/env python3
"""Discover connected USB instruments and list VISA resources.

Run this script to print `lsusb`, kernel messages, device nodes and
to try listing VISA resources via PyVISA (NI-VISA or pyvisa-py).
"""
import subprocess
import sys
import time


def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, check=False, capture_output=True, text=True)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        return "", str(e), 1


def show_section(title, out):
    sep = '=' * 8 + ' ' + title + ' ' + '=' * 8
    print(sep)
    print(out)
    print()


def list_system():
    o, e, _ = run('lsusb')
    show_section('lsusb', o or e)

    # show recent kernel messages related to USB (last 200 lines)
    o, e, _ = run('dmesg | tail -n 200')
    show_section('dmesg (last 200)', o or e)

    o, e, _ = run('usb-devices 2>/dev/null || true')
    if o:
        show_section('usb-devices', o)

    o, e, _ = run('ls -l /dev/usbtmc* /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true')
    show_section('device nodes', o or e or 'none')


def try_pyvisa():
    try:
        import pyvisa
    except Exception as exc:
        print('PyVISA not installed or failed to import:', exc)
        print('Install with: python3 -m pip install --user pyvisa pyvisa-py')
        return

    print('PyVISA version:', getattr(pyvisa, '__version__', 'unknown'))

    # Try default ResourceManager (NI-VISA if installed)
    try:
        rm = pyvisa.ResourceManager()
        res = rm.list_resources()
        print('\nResourceManager() (default) found:')
        print(res)
        for r in res:
            try:
                inst = rm.open_resource(r)
                inst.timeout = 2000
                try:
                    idn = inst.query('*IDN?')
                except Exception:
                    idn = '<no response to *IDN?>'
                print(f"{r} -> {idn}")
                inst.close()
            except Exception as e:
                print(f"{r} -> open failed: {e}")
    except Exception as e:
        print('Default ResourceManager() failed:', e)

    # Try pyvisa-py backend explicitly
    try:
        rm = pyvisa.ResourceManager('@py')
        res = rm.list_resources()
        print('\nResourceManager("@py") found:')
        print(res)
    except Exception as e:
        print('pyvisa-py ResourceManager failed or not available:', e)


def main():
    list_system()
    print('\nAttempting to list VISA resources via PyVISA...')
    try_pyvisa()


if __name__ == '__main__':
    main()
