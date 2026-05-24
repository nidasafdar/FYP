import time

try:
    from simulator_supervisor import SimulatorSupervisor
except Exception:
    from backend.simulator_supervisor import SimulatorSupervisor


def run_simulation():
    """Launcher for the per-source simulator supervisor runtime."""
    supervisor = SimulatorSupervisor()
    supervisor.start()
    print("--- Simulator supervisor started (one worker per generated source) ---")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping simulator supervisor...")
        supervisor.stop()
        print("Simulator supervisor stopped.")


if __name__ == "__main__":
    run_simulation()