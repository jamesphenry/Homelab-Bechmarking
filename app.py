from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import os
import subprocess
import json
import re
from datetime import datetime
from typing import Dict, List, Optional

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

RUNS_DIR = os.path.join(os.getcwd(), "runs")
os.makedirs(RUNS_DIR, exist_ok=True)

# Connected websockets
clients = []

# Import and initialize benchmark modules
print("🔧 Initializing benchmark modules...")

# GPU Monitoring
gpu_available = False
try:
    from benchmarks.gpu_monitor import GPUMonitor
    gpu_monitor = GPUMonitor()
    gpu_available = gpu_monitor.gpu_available
    print(f"✅ GPU Monitor: Available={gpu_available}")
except Exception as e:
    print(f"⚠️ GPU Monitor: {e}")
    gpu_available = False

# Ollama Benchmarking
ollama_available = False
try:
    from benchmarks.ollama_benchmark import OllamaBenchmark
    ollama_benchmark = OllamaBenchmark()
    ollama_available = ollama_benchmark.ollama_available
    print(f"✅ Ollama Benchmark: Available={ollama_available}")
except Exception as e:
    print(f"⚠️ Ollama Benchmark: {e}")
    ollama_available = False

# Data Parsing
try:
    from benchmarks.data_parser import BenchmarkDataParser
    data_parser = BenchmarkDataParser()
    print("✅ Data Parser: Available")
except Exception as e:
    print(f"⚠️ Data Parser: {e}")
    class FallbackBenchmarkDataParser:
        def parse_sysbench_cpu(self, output): return {}
        def parse_sysbench_memory(self, output): return {}
        def parse_sysbench_disk(self, output): return {}
        def parse_gpu_metrics(self, output): return {}
    data_parser = FallbackBenchmarkDataParser()

print(f"🖥️  CPU Count: {os.cpu_count()}")
print(f"📁 Runs Directory: {RUNS_DIR}")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    runs = [d for d in os.listdir(RUNS_DIR) if os.path.isdir(os.path.join(RUNS_DIR, d))]
    return templates.TemplateResponse("index.html", {"request": request, "runs": runs})

@app.get("/api/runs")
async def get_runs():
    """Get all benchmark runs with their data"""
    runs = []
    
    for run_name in os.listdir(RUNS_DIR):
        run_path = os.path.join(RUNS_DIR, run_name)
        if not os.path.isdir(run_path):
            continue
            
        run_info = {
            "name": run_name,
            "date": datetime.fromtimestamp(os.path.getctime(run_path)).isoformat(),
            "cpu1Thread": None,
            "cpuAllThreads": None,
            "memory": {"read": 0, "write": 0},
            "disk": {"read": 0, "write": 0},
            "gpu": {"temperature": [], "utilization": []}
        }
        
        # Load JSON data if exists
        json_path = os.path.join(run_path, "metrics.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    json_data = json.load(f)
                    run_info.update(json_data)
            except:
                pass
        
        # Parse text files for backward compatibility
        for filename in os.listdir(run_path):
            if filename.endswith('.txt'):
                filepath = os.path.join(run_path, filename)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                        
                        if 'cpu_1_thread' in filename.lower():
                            metrics = data_parser.parse_sysbench_cpu(content.split('\n'))
                            run_info['cpu1Thread'] = metrics.get('events_per_second')
                        elif 'cpu_all_threads' in filename.lower():
                            metrics = data_parser.parse_sysbench_cpu(content.split('\n'))
                            run_info['cpuAllThreads'] = metrics.get('events_per_second')
                        elif 'memory_test' in filename.lower():
                            metrics = data_parser.parse_sysbench_memory(content.split('\n'))
                            run_info['memory']['read'] = metrics.get('read_mib_sec', 0)
                            run_info['memory']['write'] = metrics.get('write_mib_sec', 0)
                        elif 'disk_test' in filename.lower():
                            metrics = data_parser.parse_sysbench_disk(content.split('\n'))
                            run_info['disk']['read'] = metrics.get('disk_read_mib_s', 0)
                            run_info['disk']['write'] = metrics.get('disk_write_mib_s', 0)
                except:
                    pass
        
        runs.append(run_info)
    
    return JSONResponse(content=sorted(runs, key=lambda x: x['date'], reverse=True))

@app.delete("/api/runs")
async def delete_all_runs():
    """Delete all benchmark runs (reset)"""
    try:
        import shutil
        if os.path.exists(RUNS_DIR):
            shutil.rmtree(RUNS_DIR)
            os.makedirs(RUNS_DIR, exist_ok=True)
            print("🗑️ All benchmark runs deleted - system reset")
            return JSONResponse(content={"message": "All runs deleted successfully", "deleted_count": "all"})
    except Exception as e:
        print(f"❌ Error deleting runs: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/api/run/{run_name}")
async def delete_run(run_name: str):
    """Delete a specific benchmark run"""
    try:
        import shutil
        run_path = os.path.join(RUNS_DIR, run_name)
        if os.path.exists(run_path):
            shutil.rmtree(run_path)
            print(f"🗑️ Run deleted: {run_name}")
            return JSONResponse(content={"message": f"Run '{run_name}' deleted successfully"})
        else:
            return JSONResponse(status_code=404, content={"error": "Run not found"})
    except Exception as e:
        print(f"❌ Error deleting run {run_name}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/ollama/models")
async def get_ollama_models():
    """Get available Ollama models"""
    try:
        # Run ollama list command
        result = await asyncio.create_subprocess_shell(
            "ollama list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()

        if result.returncode == 0:
            models_text = stdout.decode().strip()
            lines = [line.strip() for line in models_text.split('\n') if line.strip()]

            # Parse models (skip header)
            models = []
            for line in lines[1:]:  # Skip header line
                if line and not line.startswith('NAME'):
                    parts = line.split()
                    if len(parts) >= 4:  # NAME, ID, SIZE, MODIFIED
                        model_name = parts[0]
                        model_size = parts[2] if len(parts) > 2 else "Unknown"
                        models.append({
                            "name": model_name,
                            "size": model_size
                        })

            return JSONResponse(content={"models": models, "available": len(models) > 0})
        else:
            error_msg = stderr.decode().strip() if stderr else "Unknown error"
            return JSONResponse(content={"models": [], "available": False, "error": error_msg})

    except Exception as e:
        return JSONResponse(content={"models": [], "available": False, "error": str(e)})

@app.get("/api/run/{run_name}/llm")
async def get_run_llm_response(run_name: str):
    """Get LLM response for a specific run"""
    try:
        run_path = os.path.join(RUNS_DIR, run_name)
        llm_file = os.path.join(run_path, "llm_response.txt")

        if os.path.exists(llm_file):
            with open(llm_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return JSONResponse(content={"response": content, "available": True})
        else:
            return JSONResponse(content={"response": "", "available": False})

    except Exception as e:
        return JSONResponse(content={"response": "", "available": False, "error": str(e)})

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.append(ws)
    print(f"🔗 WebSocket client connected (total: {len(clients)})")
    
    try:
        while True:
            data = await ws.receive_text()
            print(f"📨 WebSocket received: {data[:50]}...")
            
            # Start benchmark if command received
            if data.startswith("run:"):
                parts = data.split(":")
                label = parts[1].strip() if len(parts) > 1 else "unnamed"
                options = {
                    "gpu": False,
                    "ollama": False,
                    "model": ""
                }
                
                # Parse options from the full data string
                if len(parts) >= 3:
                    for i in range(2, len(parts)):
                        part = parts[i].strip()
                        if part.startswith("gpu="):
                            options["gpu"] = part.split("=", 1)[1].strip().lower() == "true"
                        elif part.startswith("ollama="):
                            options["ollama"] = part.split("=", 1)[1].strip().lower() == "true"
                        elif part.startswith("model="):
                            options["model"] = part.split("=", 1)[1].strip()
                
                print(f"🚀 Starting benchmark: {label}, options: {options}")
                asyncio.create_task(run_benchmark(label, options, ws))
    except WebSocketDisconnect:
        if ws in clients:
            clients.remove(ws)
        print(f"❌ WebSocket client disconnected (remaining: {len(clients)})")

async def broadcast(message: str):
    """Broadcast message to all connected clients"""
    for client in clients[:]:  # Use slice to avoid modification during iteration
        try:
            await client.send_text(message)
        except:
            try:
                clients.remove(client)
                print("🧹 Removed disconnected client during broadcast")
            except:
                pass

async def run_benchmark(label: str, options: Dict, ws: WebSocket):
    """Run a complete benchmark suite"""
    run_dir = os.path.join(RUNS_DIR, label)
    os.makedirs(run_dir, exist_ok=True)
    
    # Initialize run data
    run_metrics = {
        "name": label,
        "date": datetime.now().isoformat(),
        "cpu1Thread": None,
        "cpuAllThreads": None,
        "memory": {"read": 0, "write": 0},
        "disk": {"read": 0, "write": 0},
        "gpu": {"temperature": [], "utilization": [], "memory_used": []},
        "ollama": {"tokens_per_sec": 0, "latency": 0, "memory_mb": 0}
    }
    
    await broadcast(f"[{label}] 🚀 Benchmark started at {datetime.now()}")
    await broadcast(f"[{label}] 📁 Results will be saved to: {run_dir}")
    
    # Define benchmark commands
    commands = [
        ("CPU 1 thread", f"sysbench cpu --threads=1 --time=20 run"),
        ("CPU all threads", f"sysbench cpu --threads={os.cpu_count()} --time=20 run"),
        ("Memory test", f"sysbench memory --memory-block-size=1M --memory-total-size=10G run"),
        ("Disk test", f"mkdir -p {run_dir}/disk && cd {run_dir}/disk && sysbench fileio --file-total-size=5G prepare && sysbench fileio --file-test-mode=seqrd run && sysbench fileio cleanup")
    ]
    
    # Add Ollama benchmark if enabled
    if options.get("ollama") and ollama_available:
        selected_model = options.get("model", "").strip()

        if selected_model:
            # Use the selected model
            await broadcast(f"[{label}] 🤖 Using selected model: {selected_model}")
            commands.append(("Ollama LLM", f"ollama run {selected_model} 'Explain quantum computing in simple terms.'"))
        else:
            # Fallback: auto-detect first available model
            await broadcast(f"[{label}] ⚠️ No model selected, auto-detecting...")
            try:
                list_result = await asyncio.create_subprocess_shell(
                    "ollama list",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await list_result.communicate()

                if list_result.returncode == 0:
                    models_text = stdout.decode().strip()
                    lines = [line.strip() for line in models_text.split('\n') if line.strip()]

                    # Skip header line and get actual model names
                    models = []
                    for line in lines[1:]:  # Skip the header line
                        if line and not line.startswith('NAME'):  # Make sure it's not a header
                            parts = line.split()
                            if parts:  # Get the first part (model name)
                                models.append(parts[0])

                    if models:
                        first_model = models[0]
                        await broadcast(f"[{label}] 🤖 Using available model: {first_model}")
                        commands.append(("Ollama LLM", f"ollama run {first_model} 'Explain quantum computing in simple terms.'"))
                    else:
                        await broadcast(f"[{label}] ⚠️ No Ollama models found. Installing llama3.1...")
                        # Try to install a basic model
                        install_result = await asyncio.create_subprocess_shell("ollama pull llama3.1:8b")
                        await install_result.communicate()
                        commands.append(("Ollama LLM", "ollama run llama3.1:8b 'Explain quantum computing in simple terms.'"))
                else:
                    await broadcast(f"[{label}] ⚠️ Failed to list Ollama models")
                    commands.append(("Ollama LLM", "echo 'Ollama not available'"))
            except Exception as e:
                await broadcast(f"[{label}] ❌ Error checking Ollama models: {str(e)}")
                commands.append(("Ollama LLM", "echo 'Ollama error occurred'"))
    elif options.get("ollama"):
        await broadcast(f"[{label}] ⚠️ Ollama not available")
    else:
        await broadcast(f"[{label}] ⚠️ Ollama benchmark disabled")
    
    # Start GPU monitoring if enabled
    gpu_monitor_task = None
    if options.get("gpu") and gpu_available:
        gpu_monitor_task = asyncio.create_task(monitor_gpu_during_benchmark(run_dir, label))
        await broadcast(f"[{label}] 🎮 GPU monitoring enabled")
    else:
        await broadcast(f"[{label}] ⚠️ GPU monitoring not available")
    
    # Run all benchmarks
    for name, cmd in commands:
        await broadcast(f"[{label}] 🔄 Running {name}...")
        print(f"Executing: {cmd}")
        
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=run_dir
            )
            
            output_lines = []
            if proc.stdout:
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    line_text = line.decode().strip()
                    output_lines.append(line_text)
                    await broadcast(f"[{label}] {name}: {line_text}")
                    
                    # Parse metrics in real-time
                    if "events per second" in line_text:
                        cpu_match = re.search(r'(\d+\.\d+)\s+events per second', line_text)
                        if cpu_match:
                            events_sec = float(cpu_match.group(1))
                            if "1 thread" in name:
                                run_metrics['cpu1Thread'] = events_sec
                            elif "all threads" in name:
                                run_metrics['cpuAllThreads'] = events_sec
            
            # Save raw output
            with open(os.path.join(run_dir, f"{name.replace(' ', '_')}.txt"), "w") as f:
                f.write("\n".join(output_lines))
            
            # Parse final metrics
            if "Memory test" in name:
                metrics = data_parser.parse_sysbench_memory(output_lines)
                run_metrics['memory']['read'] = metrics.get('read_mib_sec', 0)
                run_metrics['memory']['write'] = metrics.get('write_mib_sec', 0)
            elif "Disk test" in name:
                metrics = data_parser.parse_sysbench_disk(output_lines)
                run_metrics['disk']['read'] = metrics.get('disk_read_mib_s', 0)
                run_metrics['disk']['write'] = metrics.get('disk_write_mib_s', 0)
            elif "Ollama LLM" in name:
                # Parse Ollama metrics from output
                for line in output_lines:
                    if "Tokens/sec:" in line:
                        token_match = re.search(r'Tokens/sec:\s*(\d+\.?\d*)', line)
                        if token_match:
                            run_metrics['ollama']['tokens_per_sec'] = float(token_match.group(1))
                    elif "Latency:" in line:
                        latency_match = re.search(r'Latency:\s*(\d+\.?\d*)', line)
                        if latency_match:
                            run_metrics['ollama']['latency'] = float(latency_match.group(1))
                    elif "Memory:" in line and "MB" in line:
                        memory_match = re.search(r'Memory:\s*(\d+)', line)
                        if memory_match:
                            run_metrics['ollama']['memory_mb'] = int(memory_match.group(1))

                # Clean and save LLM response
                def clean_ansi_codes(text):
                    """Remove ANSI escape codes from text"""
                    ansi_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                    text = ansi_pattern.sub('', text)
                    # Clean up extra whitespace
                    text = re.sub(r'\n{3,}', '\n\n', text)
                    text = text.strip()
                    return text

                # Extract LLM response (everything except command output)
                response_content = '\n'.join(output_lines)
                cleaned_response = clean_ansi_codes(response_content)

                if cleaned_response.strip():
                    with open(os.path.join(run_dir, "llm_response.txt"), 'w', encoding='utf-8') as f:
                        f.write(cleaned_response)
                    await broadcast(f"[{label}] 💾 LLM response saved")
            
            await broadcast(f"[{label}] ✅ {name} completed")
            
        except Exception as e:
            await broadcast(f"[{label}] ❌ {name} failed: {str(e)}")
            print(f"Error in {name}: {e}")
    
    # Stop GPU monitoring if running
    if gpu_monitor_task:
        gpu_monitor_task.cancel()
        try:
            await gpu_monitor_task
        except asyncio.CancelledError:
            pass
    
    # Save comprehensive metrics
    metrics_path = os.path.join(run_dir, "metrics.json")
    try:
        with open(metrics_path, 'w') as f:
            json.dump(run_metrics, f, indent=2)
        await broadcast(f"[{label}] 💾 Metrics saved to {metrics_path}")
    except Exception as e:
        await broadcast(f"[{label}] ❌ Failed to save metrics: {str(e)}")
    
    # Print summary
    await broadcast(f"[{label}] 📊 Benchmark Summary:")
    if run_metrics['cpuAllThreads']:
        await broadcast(f"[{label}]   CPU Score: {run_metrics['cpuAllThreads']:.0f} events/sec")
    if run_metrics['memory']['read'] > 0:
        total_mem = run_metrics['memory']['read'] + run_metrics['memory']['write']
        await broadcast(f"[{label}]   Memory: {total_mem:.1f} MB/s")
    if run_metrics['disk']['read'] > 0:
        total_disk = run_metrics['disk']['read'] + run_metrics['disk']['write']
        await broadcast(f"[{label}]   Disk: {total_disk:.1f} MB/s")
    
    await broadcast(f"[{label}] ✅ Benchmark finished at {datetime.now()}")
    print(f"✅ Benchmark {label} completed successfully")

async def monitor_gpu_during_benchmark(run_dir: str, label: str):
    """Monitor GPU metrics during benchmark execution"""
    if not gpu_available:
        return
    
    try:
        while True:
            # Get GPU metrics
            result = await asyncio.create_subprocess_shell(
                "nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and stdout:
                gpu_data = stdout.decode().strip().split(',')
                if len(gpu_data) >= 4:
                    try:
                        temp = float(gpu_data[0].strip())
                        util = float(gpu_data[1].strip())
                        mem_used = float(gpu_data[2].strip())
                        mem_total = float(gpu_data[3].strip())
                        
                        await broadcast(f"[{label}] 🌡️ GPU: {temp:.0f}°C | ⚡ {util:.0f}% | 💾 {mem_used:.0f}/{mem_total:.0f}MB")
                        
                        # Save to GPU log file
                        with open(os.path.join(run_dir, "gpu_metrics.txt"), "a") as f:
                            f.write(f"{datetime.now().isoformat()},{temp},{util},{mem_used},{mem_total}\n")
                    except ValueError:
                        pass
            else:
                await broadcast(f"[{label}] ⚠️ GPU query failed")
            
            await asyncio.sleep(2)  # Monitor every 2 seconds
            
    except asyncio.CancelledError:
        await broadcast(f"[{label}] 🛑 GPU monitoring stopped")
        raise
    except Exception as e:
        await broadcast(f"[{label}] ❌ GPU monitoring error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Homelab Benchmark Dashboard...")
    uvicorn.run(app, host="0.0.0.0", port=8000)