import time
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Payment, RecoveryCase, Execution, AuditLog
from app.services.synthetic_data import generate_synthetic_data
from app.services.decision_engine import diagnose_and_recommend
from app.services.recovery_executor import execute_recovery
from app.services.recovery_agent import choose_intervention

SQLALCHEMY_DATABASE_URL = "sqlite:///./benchmark.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def benchmark_llm_failover(num_runs: int = 50):
    print(f"\n[benchmark] LLM failover latency ({num_runs} runs)...")
    latencies = []
    
    # Benchmark the deterministic fallback that is safe and always available.
    os.environ.pop("OPENAI_API_KEY", None)
    
    payment_data = {"failure_code": "gateway_timeout", "amount": 1500.0}
    history = {}
    
    for i in range(num_runs):
        start = time.perf_counter()
        decision = choose_intervention(payment_data["failure_code"], 80.0)
        end = time.perf_counter()
        latencies.append((end - start) * 1000) # ms
        
    avg_latency = sum(latencies) / len(latencies)
    print(f"[ok] Average deterministic fallback latency: {avg_latency:.2f} ms")
    return avg_latency

def benchmark_batch_throughput(num_cases: int = 500):
    print(f"\n[benchmark] Batch recovery throughput ({num_cases} cases)...")
    setup_db()
    db = TestingSessionLocal()
    
    print("Generating synthetic data...")
    for _ in range(5):
        generate_synthetic_data(db)
        
    cases = db.query(RecoveryCase).limit(num_cases).all()
    print(f"Executing recovery for {len(cases)} cases...")
    
    start = time.perf_counter()
    success = 0
    for c in cases:
        res = execute_recovery(db, c)
        if res["status"] == "recovered":
            success += 1
    end = time.perf_counter()
    
    duration = end - start
    rps = len(cases) / duration if duration > 0 else 0
    print(f"[ok] Processed {len(cases)} cases in {duration:.2f} seconds ({rps:.2f} cases/sec)")
    print(f"[ok] Successful recoveries: {success}")
    db.close()
    return rps

if __name__ == "__main__":
    print("="*50)
    print("RecoverAI Benchmark & Load Testing Suite")
    print("="*50)
    benchmark_llm_failover(100)
    benchmark_batch_throughput(500)
    print("\n[ok] Benchmark complete.")
