import itertools
import argparse
import json
import subprocess
import datetime
from .model import SugarscapeG1mt
from .database_logger import DatabaseLogger

def flexible_type(value):
    """
    Tries to parse the value as JSON (for lists, bools, numbers),
    otherwise returns it as a string.
    """
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value

def run_batch():
    # --- 1. Define Default Parameters ---
    DEFAULT_PARAMS = {
        "width": 50, "height": 50,
        "initial_population": 400,
        "agent_re_spawn": False,
        "sugar_regrowth_rate": 1.0,
        "endowment": [15, 15],
        "metabolism": [1, 4],
        "vision": [1, 6],
        "age": [60, 100],
        "agent_look_ahead_horizon": 25,
        "investments_enabled": True,
        "investment_portfolio_name": "default",
        "investment_json_path": "sugarscape_g1mt/investments.json",
        "log_agent_data": False,
        "seed": 42,
    }

    # --- 2. Set up Argument Parser ---
    parser = argparse.ArgumentParser(description="Run batch experiments for the Sugarscape model.")
    parser.add_argument("--replications", type=int, default=1, help="Number of times to run each parameter combination.")
    parser.add_argument("--steps", type=int, default=1000, help="Number of steps to run each simulation for.")
    parser.add_argument("--run_group", type=str, default="CLI_Batch_Run", help="A group name for this entire batch of runs.")
    parser.add_argument("--db", default="sugarscape_g1mt/simulation_results.db", help="Path to the simulation results database.")

    for key, value in DEFAULT_PARAMS.items():
        parser.add_argument(f"--{key}", type=flexible_type, default=json.dumps(value),
                            help=f"Set value(s) for '{key}'. Default: {value}")

    args = parser.parse_args()

    # --- 3. Separate Fixed vs. Varying Parameters ---
    param_space = {}
    cli_args = vars(args)
    
    for key, value in cli_args.items():
        if key in DEFAULT_PARAMS:
            is_list_of_lists = isinstance(value, list) and len(value) > 0 and isinstance(value[0], list)
            is_simple_list_for_sweep = isinstance(value, list) and key not in ["endowment", "metabolism", "vision", "age"]

            if is_list_of_lists or is_simple_list_for_sweep:
                param_space[key] = value
    
    final_fixed_params = DEFAULT_PARAMS.copy()
    for key, value in cli_args.items():
        if key in DEFAULT_PARAMS and key not in param_space:
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
                         "run_group": args.run_group, "description": description }

            run_id = logger.create_new_run(run_meta, run_params)
            
            logger.info(run_id, f"--- Running model {run_counter}/{total_runs}: {description} ---")
            
            model_init_params = run_params.copy()
            model_init_params.update({"db_logger": logger, "run_id": run_id})

            model = SugarscapeG1mt(**model_init_params)
            model.run_model(step_count=args.steps)

            logger.info(run_id, f"--- Finished run {run_counter}/{total_runs} ---")

    logger.info(None, f"Batch '{args.run_group}' complete.")

if __name__ == "__main__":
    run_batch()