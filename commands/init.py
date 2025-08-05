from state import State


async def handle_init(state: State):
    if state.is_initialized:
        print("Project is already initialized!")
        return

    state.initialize_project()
    print("ContextKit project initialized successfully!")
    print(f"Created configuration directory: {state.config_dir}")
