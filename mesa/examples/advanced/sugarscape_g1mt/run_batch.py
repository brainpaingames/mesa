# run_batch.py

import itertools
import argparse
import json
import subprocess
import datetime
from .model import SugarscapeG1mt
from .database_logger import DatabaseLogger
from .utils import load_config

def flexible_type(value):
    """
    Tries to parse the value as JSON (for lists/bools), then as a number,
    otherwise returns it as a string. This ensures that command-line
    arguments like "15" become integers, not strings.
    """
    # First, try to parse as JSON for complex types like lists or booleans
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        # If not JSON, it might be a simple number or a string
        pass

    # Next, try to cast to a number (int first, then float)
    try:
        return int(value)
    except (ValueError, TypeError):
        try:
            return float(value)
        except (ValueError, TypeError):
            # If all else fails, it's a string
            return value

def run_batch():
    # --- 1. Define Default Parameters ---
    config = load_config()
    DEFAULT_PARAMS = {}
    for section in config.values():
        DEFAULT_PARAMS.update(section)

    # --- 2. Set up Argument Parser ---
    parser = argparse.ArgumentParser(description="Run batch experiments for the Sugarscape model.")
    # Dynamically create all arguments from the config file
    for key, value in DEFAULT_PARAMS.items():
        parser.add_argument(f"--{key}", type=flexible_type, default=json.dumps(value),
                            help=f"Set value(s) for '{key}'. Default: {value}")

    args = parser.parse_args()

    # --- 3. Separate Fixed vs. Varying Parameters ---
    param_space = {}
    cli_args = vars(args)

    # This block requires a list of default keys that are part of the model/run itself.
    # We must exclude the runner controls from being considered for sweeping.
    MODEL_AND_RUN_PARAMS = {k: v for k, v in DEFAULT_PARAMS.items() if k not in ['replications', 'total_steps', 'db']}

    for key, value in cli_args.items():
        if key in MODEL_AND_RUN_PARAMS:
            is_list_of_lists = isinstance(value, list) and len(value) > 0 and isinstance(value[0], list)
            is_simple_list_for_sweep = isinstance(value, list) and key not in ["endowment", "metabolism", "vision", "age"]

            if is_list_of_lists or is_simple_list_for_sweep:
                param_space[key] = value

    final_fixed_params = MODEL_AND_RUN_PARAMS.copy()
    for key, value in cli_args.items():
        if key in MODEL_AND_RUN_PARAMS and key not in param_space:
             final_fixed_params[key] = value

    # --- 4. Generate and Run Simulations ---
    logger = DatabaseLogger(print_level=DatabaseLogger.INFO, db_path=args.db)

    if not param_space:
        param_combinations = [{}] 
    else:
        keys, values = zip(*param_space.items())
        param_combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]

    total_runs = len(param_combinations) * args.replications
    run_counter = 0

    logger.info(None, f"Starting batch '{args.run_group}' of {total_runs} total model runs...")

    try:
        git_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).strip().decode('utf-8')
    except (FileNotFoundError, subprocess.CalledProcessError):
        git_hash = "not_a_git_repo"

    for i in range(args.replications):
        for combo_params in param_combinations:
            run_counter += 1

            run_params = {**final_fixed_params, **combo_params}

            # --- 5. Expand Ranged Params to Model Params ---
            ranged_params_map = {"endowment": "endowment", "metabolism": "metabolism", "vision": "vision", "age": "agent_age"}
            for key, base_name in ranged_params_map.items():
                if key in run_params:
                    value_range = run_params.pop(key)
                    run_params[f'{base_name}_min'] = value_range[0]
                    run_params[f'{base_name}_max'] = value_range[1]

            description = ", ".join([f"{k}={v}" for k,v in combo_params.items()])
            # Handle the seed for replications
            if args.replications > 1:
                if 'seed' not in combo_params: # Don't override if seed is being swept
                    run_params['seed'] = i
                description = f"Rep {i+1}: {description}" if description else f"Rep {i+1}"

            # If seed is passed as a main arg, let it override replicator seed
            if 'seed' in cli_args and cli_args['seed'] is not None:
                run_params['seed'] = cli_args['seed']

            run_meta = { "timestamp": datetime.datetime.now().isoformat(), "git_hash": git_hash,
                         "run_group": args.run_group, "description": description, "tag": args.tag }

            run_id = logger.create_new_run(run_meta, run_params)

            logger.info(run_id, f"--- Running model {run_counter}/{total_runs}: {description} ---")

            model_init_params = run_params.copy()
            model_init_params.update({"db_logger": logger, "run_id": run_id})

            model = SugarscapeG1mt(**model_init_params)
            model.run_model(step_count=args.total_steps)

            logger.info(run_id, f"--- Finished run {run_counter}/{total_runs} ---")

    logger.info(None, f"Batch '{args.run_group}' complete.")

if __name__ == "__main__":
    run_batch()