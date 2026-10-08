import time
import threading
import numpy as np

class SystemState:
    def __init__(self, state_vector, weight_matrix):
        self.state_vector = np.array(state_vector, dtype=float) # [MemoryRisk, ConnRisk]
        self.weight_matrix = np.array(weight_matrix, dtype=float)
        self.epistemic_variance = 0.0

class DualEngine:
    def __init__(self, initial_state: SystemState, sampling_rate_sec: float, clock_rate_sec: float):
        self.state = initial_state
        self.sampling_rate = sampling_rate_sec
        self.clock_rate = clock_rate_sec
        self.lock = threading.Lock() # Protects state modifications
        self.running = False

    def get_state_snapshot(self):
        with self.lock:
            return self.state

    def run_main_log_interval(self):
        """Tier 1-4 fast snapshot calculations executing on log arrivals"""
        while self.running:
            time.sleep(self.sampling_rate)
            
            # Fetch safe state reference
            current_state = self.get_state_snapshot()
            
            # Tier 4 Operator shortcut: Laplace Analytical Drift computation
            # s-domain lookup approximation across interval
            drift_factor = 0.015 * np.exp(self.sampling_rate / 60.0)
            current_state.state_vector[0] = min(current_state.state_vector[0] + drift_factor, 1.0)
            
            # Linear Algebra Matrix-Vector Product (y = Ax)
            downstream_risk = np.dot(current_state.weight_matrix, current_state.state_vector)
            
            # Accumulate background truncation leak
            current_state.epistemic_variance += 0.005
            print(f"[MAIN LOOP] Processed Log Interval. Computed System Downstream Matrix Impact: {downstream_risk} | Accumulating Drift: {current_state.epistemic_variance:.4f}")

    def run_system_clock_daemon(self):
        """Asynchronous background thread running on system clock to pull raw logs and clear drift"""
        while self.running:
            time.sleep(self.clock_rate)
            print("[SYSTEM CLOCK] Background Daemon Awoken. Running Deep Calculus Reset...")
            
            # Perform expensive integration formulas over raw storage records
            # Mimicking real-time ODE tracking to correct numerical shortcut drift
            time.sleep(0.05) 
            
            # Prepare freshly calibrated vectors
            pure_state_vector = np.array([0.12, 0.04]) # Ground truth re-anchored
            
            # Atomic state update under exclusive lock protection
            with self.lock:
                self.state.state_vector = pure_state_vector
                self.state.epistemic_variance = 0.0 # Fluid risk volume completely drained
                
            print("[SYSTEM CLOCK] Re-anchor Complete. Main loop state variables normalized natively.")

    def start(self):
        self.running = True
        self.main_thread = threading.Thread(target=self.run_main_log_interval, daemon=True)
        self.clock_thread = threading.Thread(target=self.run_system_clock_daemon, daemon=True)
        
        self.main_thread.start()
        self.clock_thread.start()

    def stop(self):
        self.running = False
