import sqlite3
import datetime
import json

class DatabaseLogger:
    """
    Handles logging simulation data and text messages to a SQLite database.
    This version is thread-safe by creating a new connection for each
    transaction, which is necessary for use with multi-threaded servers
    like Solara.
    """
    # Define standard logging levels
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    LEVEL_NAMES = {
        DEBUG: "DEBUG",
        INFO: "INFO",
        WARNING: "WARNING",
        ERROR: "ERROR",
        CRITICAL: "CRITICAL",
    }

    def __init__(self, db_path="simulation_results.db", print_level=INFO):
        self.db_path = db_path
        self.print_level = print_level
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
                    description TEXT,
                    tag TEXT
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs (run_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS spatial_data (
                    run_id INTEGER NOT NULL,
                    step INTEGER NOT NULL,
                    layer_name TEXT NOT NULL,
                    layer_data TEXT NOT NULL,
                    PRIMARY KEY (run_id, step, layer_name),
                    FOREIGN KEY (run_id) REFERENCES runs (run_id)
                )
            """)
            conn.commit()

    def _log(self, run_id: int, level: int, message: str):
        """Core logging method. Writes to DB and conditionally prints."""
        level_name = self.LEVEL_NAMES.get(level, "UNKNOWN")
        timestamp = datetime.datetime.now().isoformat()
        
        # Always log to the database
        with self._get_connection() as conn:
            sql = "INSERT INTO logs (run_id, timestamp, level, message) VALUES (?, ?, ?, ?)"
            conn.execute(sql, (run_id, timestamp, level_name, message))
            conn.commit()

        # Conditionally print to stdout
        if level >= self.print_level:
            print(f"[{timestamp}] [{level_name}] {message}")

    # Public helper methods for convenience
    def debug(self, run_id, message):
        self._log(run_id, self.DEBUG, message)
    
    def info(self, run_id, message):
        self._log(run_id, self.INFO, message)

    def warning(self, run_id, message):
        self._log(run_id, self.WARNING, message)

    def error(self, run_id, message):
        self._log(run_id, self.ERROR, message)

    def critical(self, run_id, message):
        self._log(run_id, self.CRITICAL, message)

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
            
    def log_static_run_parameter(self, run_id, key, value):
        """Logs a single key-value parameter for a run, useful for static data."""
        with self._get_connection() as conn:
            sql = "INSERT INTO run_parameters (run_id, parameter_name, parameter_value) VALUES (?, ?, ?)"
            conn.execute(sql, (run_id, key, value))
            conn.commit()

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
                    if value is not None:
                        agent_data_to_log.append((run_id, step, agent.unique_id, key, value))
            
            cursor.executemany("INSERT INTO agent_data (run_id, step, agent_id, attribute_name, attribute_value) VALUES (?, ?, ?, ?, ?)", agent_data_to_log)
            conn.commit()
            
    def log_spatial_layer(self, run_id: int, step: int, layer_name: str, layer_data_array):
        """Logs a full 2D spatial layer for a single step."""
        with self._get_connection() as conn:
            # Convert numpy array to native Python list for JSON serialization
            layer_data_list = layer_data_array.tolist()
            layer_data_json = json.dumps(layer_data_list)
            
            sql = "INSERT INTO spatial_data (run_id, step, layer_name, layer_data) VALUES (?, ?, ?, ?)"
            conn.execute(sql, (run_id, step, layer_name, layer_data_json))
            conn.commit()

    def close(self):
        # This method is no longer strictly necessary, as we don't hold a
        # persistent connection, but it's good practice to leave it in case
        # the connection strategy changes later.
        pass