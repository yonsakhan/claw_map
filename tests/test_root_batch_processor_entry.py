import unittest
from unittest.mock import patch

import batch_processor
from src.analysis.batch_processor import BatchProcessor as SrcBatchProcessor


class TestRootBatchProcessorEntry(unittest.TestCase):
    def test_root_batch_processor_reexports_src_batch_processor(self):
        self.assertIs(batch_processor.BatchProcessor, SrcBatchProcessor)

    def test_root_main_delegates_to_src_batch_processor(self):
        calls = []

        async def dummy_coro():
            return None

        class ProcessorStub:
            def process(self, *, limit, skip_existing):
                calls.append({"limit": limit, "skip_existing": skip_existing})
                return dummy_coro()

        processor_mock = ProcessorStub()

        with (
            patch("batch_processor.BatchProcessor", return_value=processor_mock) as processor_cls,
            patch("batch_processor.asyncio.run") as asyncio_run,
        ):
            batch_processor.main()

        processor_cls.assert_called_once_with(
            input_file="dummy_data.jsonl",
            output_file="structured_personas.jsonl",
        )
        asyncio_run.assert_called_once()
        coroutine = asyncio_run.call_args.args[0]
        self.assertTrue(hasattr(coroutine, "close"))
        coroutine.close()
        self.assertEqual(calls, [{"limit": 10, "skip_existing": False}])

    def test_root_run_cli_initializes_logging_and_delegates(self):
        with (
            patch("batch_processor.logging.basicConfig"),
            patch("batch_processor.main") as main_mock,
        ):
            batch_processor.run_cli()

        main_mock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
