import json
import logging

import pandas as pd

from src.db.session import get_engine


logger = logging.getLogger(__name__)

class AnalysisDashboard:
    def __init__(self, data_file: str = "structured_personas.jsonl", use_postgres: bool = True):
        self.data_file = data_file
        self.use_postgres = use_postgres
        self.data_source = "unknown"
        self.load_error: str | None = None
        self.df = self._load_data()

    def _load_data(self) -> pd.DataFrame:
        if self.use_postgres:
            try:
                engine = get_engine()
                query = """
                SELECT original_id, age_group, location, fertility_status, income_level, spatial_preferences, fertility_intent_score
                FROM agent_personas
                """
                df = pd.read_sql(query, engine)
                self.data_source = "postgres"
                self.load_error = None
                return df
            except Exception as exc:
                self.load_error = f"postgres load failed: {exc}"
                logger.warning(self.load_error)
        data = []
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            missing_msg = f"File {self.data_file} not found."
            self.load_error = f"{self.load_error}; {missing_msg}" if self.load_error else missing_msg
            logger.warning(missing_msg)
            return pd.DataFrame()

        self.data_source = "jsonl"
        return pd.DataFrame(data)

    def generate_report(self):
        if self.df.empty:
            print("No data to analyze.")
            return

        print("\n=== Digital Demographics Report ===")
        print(f"Total Personas: {len(self.df)}")
        print(f"Data Source: {self.data_source}")
        if self.load_error:
            print(f"Load Warning: {self.load_error}")
        
        if "age_group" in self.df.columns:
            print("\nAge Distribution:")
            print(self.df["age_group"].value_counts(normalize=True).mul(100).round(1).astype(str) + "%")

        if "income_level" in self.df.columns:
            print("\nIncome Level Distribution:")
            print(self.df["income_level"].value_counts(normalize=True).mul(100).round(1).astype(str) + "%")

        if "fertility_status" in self.df.columns:
            print("\nFertility Status Distribution:")
            print(self.df["fertility_status"].value_counts(normalize=True).mul(100).round(1).astype(str) + "%")

        if "fertility_intent_score" in self.df.columns:
            print("\nAverage Fertility Intent Score by Income:")
            print(self.df.groupby("income_level")["fertility_intent_score"].mean().round(2))

        print("\n===================================")

if __name__ == "__main__":
    dashboard = AnalysisDashboard()
    dashboard.generate_report()
