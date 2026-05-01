import asyncio
import logging

from src.analysis.batch_processor import BatchProcessor


logger = logging.getLogger("BatchProcessorCompat")


def main():
    logger.warning("root batch_processor.py is deprecated; delegating to src.analysis.batch_processor.")
    processor = BatchProcessor(
        input_file="dummy_data.jsonl",
        output_file="structured_personas.jsonl",
    )
    asyncio.run(processor.process(limit=10, skip_existing=False))


def run_cli():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()


if __name__ == "__main__":
    run_cli()
