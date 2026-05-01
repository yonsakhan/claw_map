import unittest
from unittest.mock import patch

import db_setup
import fix_display_name
import local_login
import scripts.db_setup
import scripts.fix_display_name
import scripts.local_login


class TestScriptsEntrypoints(unittest.TestCase):
    def test_root_db_setup_reexports_scripts_module(self):
        self.assertIs(db_setup.main, scripts.db_setup.main)
        self.assertIs(db_setup.init_db, scripts.db_setup.init_db)
        self.assertIs(db_setup.migrate_agent_personas_columns, scripts.db_setup.migrate_agent_personas_columns)

    def test_root_local_login_reexports_scripts_module(self):
        self.assertIs(local_login.main, scripts.local_login.main)
        self.assertIs(local_login._parse_args, scripts.local_login._parse_args)
        self.assertIs(local_login._resolve_login_options, scripts.local_login._resolve_login_options)

    def test_root_fix_display_name_reexports_scripts_module(self):
        self.assertIs(fix_display_name.main, scripts.fix_display_name.main)
        self.assertIs(fix_display_name.process_file, scripts.fix_display_name.process_file)
        self.assertIs(fix_display_name.fix_record, scripts.fix_display_name.fix_record)

    def test_root_db_setup_run_cli_warns_and_delegates(self):
        with (
            patch("db_setup.logging.basicConfig"),
            patch("db_setup.logger.warning") as warning_mock,
            patch("db_setup.main") as main_mock,
        ):
            db_setup.run_cli()

        warning_mock.assert_called_once()
        main_mock.assert_called_once_with()

    def test_root_local_login_run_cli_warns_and_delegates(self):
        with (
            patch("local_login.logging.basicConfig"),
            patch("local_login.logger.warning") as warning_mock,
            patch("local_login.asyncio.run") as asyncio_run,
            patch("local_login.main") as main_mock,
        ):
            local_login.run_cli()

        warning_mock.assert_called_once()
        main_mock.assert_called_once_with()
        asyncio_run.assert_called_once()
        coroutine = asyncio_run.call_args.args[0]
        self.assertTrue(hasattr(coroutine, "close"))
        coroutine.close()

    def test_root_fix_display_name_run_cli_warns_and_exits(self):
        with (
            patch("fix_display_name.logging.basicConfig"),
            patch("fix_display_name.logger.warning") as warning_mock,
            patch("fix_display_name.main", return_value=0) as main_mock,
        ):
            with self.assertRaises(SystemExit) as cm:
                fix_display_name.run_cli()

        self.assertEqual(cm.exception.code, 0)
        warning_mock.assert_called_once()
        main_mock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
