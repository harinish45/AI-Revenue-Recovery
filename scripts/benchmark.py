import time
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Payment, RecoveryCase, Execution, AuditLog
from app.services.synthetic_data import generate_synthetic_payments
from app.services.decision_engine import diagnose_and_recommend
from app.services.recovery_executor import execute_recovery
from app.services.llm_provider_chain import chain

SQLALCHEMY_DATABASE_URL = "sqlite:///./benchmark.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def benchmark_llm_failover(num_runs: int = 50):
    print(f"\n\U0001f680 Benchmarking LLM Failover Latency ({num_runs} runs)...")
    latencies = []
    
    # Ensure OpenAI provider fails by not setting API key
    os.environ.pop("OPENAI_API_KEY", None)
    
    payment_data = {"failure_code": "gateway_timeout", "amount": 1500.0}
    history = {}
    
    for i in range(num_runs):
        start = time.perf_counter()
        decision = chain.get_decision(payment_data, history)
        end = time.perf_counter()
        latencies.append((end - start) * 1000) # ms
        
    avg_latency = sum(latencies) / len(latencies)
    print(f"\u2705 Average Failover Latency to DeterministicFallbackProvider: {avg_latency:.2f} ms")
    return avg_latency

def benchmark_batch_throughput(num_cases: int = 500):
    print(f"\n\U0001f680 Benchmarking Batch Recovery Throughput ({num_cases} cases)...")
    setup_db()
    db = TestingSessionLocal()
    
    print("Generating synthetic data...")
    for _ in range(5):
        generate_synthetic_payments(db, 100)
        
    cases = db.query(RecoveryCase).limit(num_cases).all()
    print(f"Executing recovery for {len(cases)} cases...")
    
    start = time.perf_counter()
    success = 0
    for c in cases:
        res = execute_recovery(db, c)
        if res["status"] == "RECOVERED":
            success += 1
    end = time.perf_counter()
    
    duration = end - start
    rps = len(cases) / duration if duration > 0 else 0
    print(f"\u2705 Processed {len(cases)} cases in {duration:.2f} seconds ({rps:.2f} cases/sec)")
    print(f"\u2705 Successful recoveries: {success}")
    db.close()
    return rps

if __name__ == "__main__":
    print("="*50)
    print("RecoverAI Benchmark & Load Testing Suite")
    print("="*50)
    benchmark_llm_failover(100)
    benchmark_batch_throughput(500)
    print("\n\U0001f389 Benchmark Complete.")
