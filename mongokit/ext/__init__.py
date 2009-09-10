
__all__ = []

try:
    import pylons
    from pylons_env import MongoPylonsEnv
    __all__ += ['MongoPylonsEnv']
except:
    pass
