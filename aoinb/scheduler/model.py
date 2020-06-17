import enum


class ClientStatus(enum.IntEnum):
    not_connected = -1
    waiting = 0
    downloading = 1
    building = 2

