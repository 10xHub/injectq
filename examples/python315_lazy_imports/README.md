# Python 3.15 lazy imports with InjectQ

A runnable demo of Python 3.15 explicit lazy imports ([PEP 810](https://peps.python.org/pep-0810/)) with InjectQ. It shows:

- the startup speedup
- the one thing to watch, which is services that register themselves on import
- three ways to fix it

`services.py`, `reports.py` and `sms.py` print a line when they load, so you can see exactly when Python loads them.

The full guide is in [docs/getting-started/lazy-imports.md](../../docs/getting-started/lazy-imports.md).

## Run it

You need InjectQ 0.5.0+ installed. Use Python 3.15 to see lazy mode; on 3.10 to 3.14 the demo still runs, but everything is imported eagerly.

```bash
cd examples/python315_lazy_imports
python3.15 run_demo.py
```

`run_demo.py` runs each step twice, once with normal imports and once with `PYTHON_LAZY_IMPORTS=all`. You can also run any step on its own; the docstring at the top of each file shows the commands.

## The steps

| File | What it shows |
|---|---|
| `step1_global_lazy_startup.py` | Global lazy mode (`PYTHON_LAZY_IMPORTS=all`): a slow module (`reports.py`, 1 second) isn't loaded at startup, and only loads with `--report`. `@singleton` and `@inject` work unchanged. |
| `step2_lazy_modules_startup.py` | Per-module opt-in with `__lazy_modules__ = ["reports"]`. Lazy on 3.15 even without the environment variable; ignored on 3.10 to 3.14. |
| `step3_registration_problem.py` | The problem: `import services` is there only so `@register_as` runs. Under global lazy mode the module never loads, and resolving `Notifier` fails. |
| `step4_fix_importlib.py` | Fix 1: `importlib.import_module("services")` always runs right away. |
| `step5_fix_filter.py` | Fix 2: `sys.set_lazy_imports_filter` keeps `services` eager while everything else stays lazy. |
| `step6_fix_setup_function.py` | Fix 3: register explicitly in `setup_container()` (`wiring.py`) instead of relying on import side effects. |

Supporting modules:

- `interfaces.py` defines `Notifier`.
- `services.py` registers `EmailNotifier` with `@register_as` when it's imported.
- `sms.py` has a plain `SmsNotifier` with no decorator.
- `wiring.py` binds `SmsNotifier` explicitly.
- `reports.py` is the slow module.

## What you'll see on Python 3.15

Step 1, startup time:

```
--- normal imports ---
  [reports] loading heavy module (1 second)...
imports finished after 1.05s
hello from an injected singleton

--- PYTHON_LAZY_IMPORTS=all ---
imports finished after 0.00s
hello from an injected singleton
```

Step 3, the problem:

```
--- normal imports ---
  [services] module loaded -> EmailNotifier registered for Notifier
email sent: hi

--- PYTHON_LAZY_IMPORTS=all ---
FAILED: No binding found for type: <class 'interfaces.Notifier'>
  'services' was never loaded, so @register_as never ran.
```

Steps 4 to 6 print `email sent: hi` or `sms sent: hi` in both modes.
