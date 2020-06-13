import configparser


def make_insert(d):
    keys, values = zip(*d.items())
    return ', '.join(keys), ', '.join(('%s',) * len(values)), values


def make_update(d):
    keys, values = zip(*d.items())
    return ', '.join(k + '=%s' for k in keys), values


def make_where(d):
    keys, values = zip(*d.items())
    return ' AND '.join(k + '=%s' for k in keys), values


def load_config(filename):
    config = configparser.ConfigParser(interpolation=None)
    config.read(filename, 'utf-8')
    return config


class AttrDict(dict):
    """Dict with attribute access."""
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


