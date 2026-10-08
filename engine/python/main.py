from dual_engine import DualEngine, SystemState

if __name__ == "__main__":
    # Initialize component matrix allocations
    init_state = SystemState(
        state_vector=[0.12, 0.04],
        weight_matrix=[[0.85, 0.15], [0.30, 0.70]]
    )

    # Ingest logs every 1.0 seconds, re-anchor off system clock every 4.0 seconds
    engine = DualEngine(init_state, sampling_rate_sec=1.0, clock_rate_sec=4.0)
    
    try:
        engine.start()
        import time as sys_time
        sys_time.sleep(10) # Run for 10 seconds to watch the thread interactions
    finally:
        engine.stop()
