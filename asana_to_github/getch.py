# Stupid pypi getch module needs to compile a C extension.
# And readchar doesn't handle control chars (Ctrl+C, for example).
# WHHHYYYY?
# So just use a SO snippet.
import sys
import tty
import termios


def readchar():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def getch():
    char = readchar()
    if char == '\x03':
        raise KeyboardInterrupt
    elif char == '\x04':
        raise EOFError
    return char
