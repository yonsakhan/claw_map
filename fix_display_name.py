"""Legacy top-level display-name fixer entrypoint."""

import logging

from scripts import fix_display_name as _impl

TARGET_BROKEN_NAME = _impl.TARGET_BROKEN_NAME
resolve_input_path = _impl.resolve_input_path
infer_display_name = _impl.infer_display_name
fix_record = _impl.fix_record
load_jsonl = _impl.load_jsonl
write_jsonl = _impl.write_jsonl
process_file = _impl.process_file
main = _impl.main
logger = logging.getLogger("FixDisplayNameCompat")


def run_cli():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.warning("root fix_display_name.py is deprecated; use `python -m scripts.fix_display_name`.")
    raise SystemExit(main())


if __name__ == "__main__":
    run_cli()
