import sqlite3
import sys
import argparse

class RunManager:
    def __init__(self, db_path="simulation_results.db"):
        self.db_path = db_path

    def _get_connection(self):
        """Helper method to get a new database connection."""
        return sqlite3.connect(self.db_path)

    def delete_run(self, run_id):
        """Delete a run by ID and all related data."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM run_parameters WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM model_results WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM agent_data WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM logs WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM spatial_data WHERE run_id = ?", (run_id,))
            conn.commit()
            print(f"Run {run_id} and all related data have been deleted.")

    def delete_runs_less_than(self, run_id):
        """Delete runs with IDs less than a given number."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM runs WHERE run_id < ?", (run_id,))
            cursor.execute("DELETE FROM run_parameters WHERE run_id < ?", (run_id,))
            cursor.execute("DELETE FROM model_results WHERE run_id < ?", (run_id,))
            cursor.execute("DELETE FROM agent_data WHERE run_id < ?", (run_id,))
            cursor.execute("DELETE FROM logs WHERE run_id < ?", (run_id,))
            cursor.execute("DELETE FROM spatial_data WHERE run_id < ?", (run_id,))
            conn.commit()
            print(f"All runs with IDs less than {run_id} and all related data have been deleted.")

    def delete_runs_by_group(self, group_string):
        """Delete runs whose run_group contains a given string."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM runs WHERE run_group LIKE ?", ('%' + group_string + '%',))
            cursor.execute("DELETE FROM run_parameters WHERE run_id IN (SELECT run_id FROM runs WHERE run_group LIKE ?)", ('%' + group_string + '%',))
            cursor.execute("DELETE FROM model_results WHERE run_id IN (SELECT run_id FROM runs WHERE run_group LIKE ?)", ('%' + group_string + '%',))
            cursor.execute("DELETE FROM agent_data WHERE run_id IN (SELECT run_id FROM runs WHERE run_group LIKE ?)", ('%' + group_string + '%',))
            cursor.execute("DELETE FROM logs WHERE run_id IN (SELECT run_id FROM runs WHERE run_group LIKE ?)", ('%' + group_string + '%',))
            cursor.execute("DELETE FROM spatial_data WHERE run_id IN (SELECT run_id FROM runs WHERE run_group LIKE ?)", ('%' + group_string + '%',))
            conn.commit()
            print(f"All runs with run_group containing '{group_string}' and all related data have been deleted.")

    def tag_run(self, run_id, tag):
        """Tag a run with 'dev', 'test', or 'prod'."""
        if tag not in ["dev", "test", "prod"]:
            print("Invalid tag. Please use 'dev', 'test', or 'prod'.")
            return

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE runs SET tag = ? WHERE run_id = ?", (tag, run_id))
            conn.commit()
            print(f"Run {run_id} has been tagged with '{tag}'.")

def main():
    parser = argparse.ArgumentParser(description="Manage runs in the simulation_results.db database.")
    subparsers = parser.add_subparsers(dest="command")

    # Delete run by ID
    parser_delete_run = subparsers.add_parser("delete_run", help="Delete a run by ID.")
    parser_delete_run.add_argument("run_id", type=int, help="The ID of the run to delete.")

    # Delete runs less than ID
    parser_delete_less_than = subparsers.add_parser("delete_less_than", help="Delete runs with IDs less than a given number.")
    parser_delete_less_than.add_argument("run_id", type=int, help="The ID threshold for deleting runs.")

    # Delete runs by group
    parser_delete_by_group = subparsers.add_parser("delete_by_group", help="Delete runs whose run_group contains a given string.")
    parser_delete_by_group.add_argument("group_string", type=str, help="The string to search for in the run_group.")

    # Tag run
    parser_tag_run = subparsers.add_parser("tag_run", help="Tag a run with 'dev', 'test', or 'prod'.")
    parser_tag_run.add_argument("run_id", type=int, help="The ID of the run to tag.")
    parser_tag_run.add_argument("tag", type=str, help="The tag to apply to the run ('dev', 'test', or 'prod').")

    args = parser.parse_args()

    manager = RunManager()

    if args.command == "delete_run":
        manager.delete_run(args.run_id)
    elif args.command == "delete_less_than":
        manager.delete_runs_less_than(args.run_id)
    elif args.command == "delete_by_group":
        manager.delete_runs_by_group(args.group_string)
    elif args.command == "tag_run":
        manager.tag_run(args.run_id, args.tag)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
