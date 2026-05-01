import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, inspect, text

from scripts import db_setup


class TestDbSetup(unittest.TestCase):
    def test_migrate_agent_personas_columns_adds_missing_columns(self):
        engine = create_engine("sqlite:///:memory:")
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        CREATE TABLE agent_personas (
                            id INTEGER PRIMARY KEY,
                            original_id VARCHAR
                        )
                        """
                    )
                )

            db_setup.migrate_agent_personas_columns(engine)

            columns = {column["name"] for column in inspect(engine).get_columns("agent_personas")}
            self.assertIn("questionnaire_answers", columns)
            self.assertIn("reasoning_summary", columns)
            self.assertIn("created_at", columns)
        finally:
            engine.dispose()

    def test_migrate_agent_personas_columns_skips_when_table_missing(self):
        engine = create_engine("sqlite:///:memory:")
        try:
            db_setup.migrate_agent_personas_columns(engine)
            self.assertNotIn("agent_personas", inspect(engine).get_table_names())
        finally:
            engine.dispose()

    def test_init_db_creates_tables_and_runs_migration(self):
        engine = create_engine("sqlite:///:memory:")
        try:
            with (
                patch("scripts.db_setup.get_engine", return_value=engine),
                patch("scripts.db_setup.migrate_agent_personas_columns") as migrate_mock,
            ):
                db_setup.init_db()

            migrate_mock.assert_called_once_with(engine)
        finally:
            engine.dispose()

    def test_main_delegates_to_init_db(self):
        with patch("scripts.db_setup.init_db") as init_db_mock:
            db_setup.main()

        init_db_mock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
