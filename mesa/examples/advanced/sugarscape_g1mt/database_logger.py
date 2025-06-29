import sqlite3

class DatabaseLogger:
    """
    Handles logging simulation data to a SQLite database.
    This version is thread-safe by creating a new connection for each
    transaction, which is necessary for use with multi-threaded servers
    like Solara.
    """

    def __init__(self, db_path="simulation_results.db"):
        self.db_path = db_path
        # We no longer connect in the constructor.
        # We only create the tables if they don't exist.
        self._create_tables()

    def _get_connection(self):
        """Helper method to get a new database connection."""
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        """Creates the necessary tables using a temporary connection."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    git_hash TEXT NOT NULL,
                    run_group TEXT,
                    description TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS run_parameters (
                    run_id INTEGER NOT NULL,
                    parameter_name TEXT NOT NULL,
                    parameter_value NUMERIC NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs (run_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_results (
                    run_id INTEGER NOT NULL,
                    step INTEGER NOT NULL,
                    reporter_name TEXT NOT NULL,
                    reporter_value NUMERIC NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs (run_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_data (
                    run_id INTEGER NOT NULL,
                    step INTEGER NOT NULL,
                    agent_id INTEGER NOT NULL,
                    attribute_name TEXT NOT NULL,
                    attribute_value NUMERIC NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs (run_id)
                )
            """)
            conn.commit()

    def create_new_run(self, run_meta: dict, model_params: dict):
        """Creates a new run record and logs its parameters."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            sql = "INSERT INTO runs (timestamp, git_hash, run_group, description) VALUES (?, ?, ?, ?)"
            values = (run_meta['timestamp'], run_meta['git_hash'], run_meta['run_group'], run_meta['description'])
            cursor.execute(sql, values)
            run_id = cursor.lastrowid

            param_data = [(run_id, key, value) for key, value in model_params.items()]
            cursor.executemany("INSERT INTO run_parameters (run_id, parameter_name, parameter_value) VALUES (?, ?, ?)", param_data)

            conn.commit()
            return run_id

    def log_model_step(self, run_id: int, step: int, model_vars: dict):
        """Logs aggregated model-level results for a single step."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            result_data = [(run_id, step, key, value) for key, value in model_vars.items()]
            cursor.executemany("INSERT INTO model_results (run_id, step, reporter_name, reporter_value) VALUES (?, ?, ?, ?)", result_data)
            conn.commit()

    def log_agent_data(self, run_id: int, step: int, agents):
        """Logs individual agent data for a single step."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            agent_data_to_log = []
            for agent in agents:
                attributes = agent.get_reportable_attributes()
                for key, value in attributes.items():
                    agent_data_to_log.append((run_id, step, agent.unique_id, key, value))
            
            cursor.executemany("INSERT INTO agent_data (run_id, step, agent_id, attribute_name, attribute_value) VALUES (?, ?, ?, ?, ?)", agent_data_to_log)
            conn.commit()

    def close(self):
        # This method is no longer strictly necessary, as we don't hold a
        # persistent connection, but it's good practice to leave it in case
        # we change the connection strategy later.
        pass