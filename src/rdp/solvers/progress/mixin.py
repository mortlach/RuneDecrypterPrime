from __future__ import annotations

class ProgressMixin:
    def _log(self, logger, **fields):
        if logger:
            logger.write(str(fields))
