"""Mock structlog pour tests sans installation."""
import sys
import types

class _Logger:
    def __getattr__(self, name):
        def noop(*args, **kwargs): pass
        return noop

class _FakeStructlog(types.ModuleType):
    def get_logger(self, *a, **k): return _Logger()
    def configure(self, **k): pass
    def make_filtering_bound_logger(self, level): return _Logger
    PrintLoggerFactory = type('PLF', (), {'__call__': lambda s: None})
    stdlib = type('stdlib', (), {
        'add_log_level': lambda e, m, v: v,
        'add_logger_name': lambda e, m, v: v,
    })()
    dev = type('dev', (), {
        'ConsoleRenderer': lambda **k: (lambda e, m, v: str(v))
    })()
    processors = type('proc', (), {
        'TimeStamper': lambda **k: (lambda e, m, v: v)
    })()

sys.modules['structlog'] = _FakeStructlog('structlog')
