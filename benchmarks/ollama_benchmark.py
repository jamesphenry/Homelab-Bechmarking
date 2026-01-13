"""
Ollama LLM Benchmarking utilities
"""
import asyncio
import subprocess
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional

class OllamaBenchmark:
    def __init__(self):
        self.ollama_available = self._check_ollama_available()
        self.models = []
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            result = subprocess.run(['ollama', '--version'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    async def get_available_models(self) -> List[str]:
        """Get list of available Ollama models"""
        if not self.ollama_available:
            return []
        
        try:
            result = await asyncio.create_subprocess_shell(
                'ollama list',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                return []
            
            models = []
            lines = stdout.decode().strip().split('\n')
            
            for line in lines[1:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 1:
                        models.append(parts[0])
            
            return models
            
        except:
            return []
    
    async def benchmark_model(self, model: str, prompt: str = "Explain quantum computing in simple terms.", max_tokens: int = 500) -> Dict:
        """Benchmark a specific Ollama model"""
        if not self.ollama_available:
            return {'error': 'Ollama not available'}
        
        start_time = time.time()
        
        try:
            # Create the command
            cmd = f'ollama run {model} "{prompt}"'
            
            result = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            output_lines = []
            first_token_time = None
            total_tokens = 0
            
            # Read output in real-time
            if result.stdout:
                while True:
                    line = await result.stdout.readline()
                    if not line:
                        break
                    
                    line_text = line.decode()
                    output_lines.append(line_text)
                    
                    # Record first token time
                    if first_token_time is None and line_text.strip():
                        first_token_time = time.time() - start_time
                    
                    # Count tokens (rough estimation)
                    total_tokens += len(line_text.split())
            
            end_time = time.time()
            
            # Calculate metrics
            total_time = end_time - start_time
            time_to_first_token = first_token_time if first_token_time else total_time
            tokens_per_second = total_tokens / total_time if total_time > 0 else 0
            
            # Get memory usage
            memory_usage = await self._get_model_memory_usage(model)
            
            benchmark_result = {
                'model': model,
                'prompt': prompt,
                'total_time': total_time,
                'time_to_first_token': time_to_first_token,
                'total_tokens': total_tokens,
                'tokens_per_second': tokens_per_second,
                'memory_usage_mb': memory_usage,
                'output': ''.join(output_lines),
                'timestamp': datetime.now().isoformat(),
                'success': True
            }
            
            return benchmark_result
            
        except Exception as e:
            return {
                'model': model,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'success': False
            }
    
    async def _get_model_memory_usage(self, model: str) -> float:
        """Estimate memory usage for a model"""
        try:
            # This is a rough estimation - in a real implementation,
            # you might monitor nvidia-smi during inference
            result = await asyncio.create_subprocess_shell(
                f'ollama show {model} --format json',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                model_info = json.loads(stdout.decode())
                # Extract parameter count and estimate memory
                parameters = model_info.get('details', {}).get('parameter_count', 0)
                # Rough estimation: 1B parameters ≈ 2GB VRAM for FP16
                estimated_memory = (parameters / 1e9) * 2048 if parameters else 0
                return estimated_memory
            
        except:
            pass
        
        return 0.0
    
    async def run_comprehensive_benchmark(self, models: Optional[List[str]] = None) -> Dict:
        """Run comprehensive benchmarks on multiple models"""
        if not self.ollama_available:
            return {'error': 'Ollama not available'}
        
        if models is None:
            models = await self.get_available_models()
            if not models:
                return {'error': 'No models available'}
        
        if not models:
            return {'error': 'No models available'}
        
        # Define test prompts for different scenarios
        test_prompts = [
            {
                'name': 'simple_generation',
                'prompt': 'Write a short poem about technology.',
                'expected_tokens': 100
            },
            {
                'name': 'complex_reasoning',
                'prompt': 'Explain the relationship between machine learning and artificial intelligence, including key concepts and differences.',
                'expected_tokens': 300
            },
            {
                'name': 'coding_task',
                'prompt': 'Write a Python function that calculates the factorial of a number using recursion.',
                'expected_tokens': 50
            }
        ]
        
        results = {}
        
        for model in models:
            model_results = {
                'model': model,
                'benchmarks': []
            }
            
            for test in test_prompts:
                print(f"Benchmarking {model} with {test['name']}...")
                
                result = await self.benchmark_model(
                    model=model,
                    prompt=test['prompt'],
                    max_tokens=test['expected_tokens']
                )
                
                result['test_name'] = test['name']
                result['expected_tokens'] = test['expected_tokens']
                model_results['benchmarks'].append(result)
            
            # Calculate aggregate metrics
            successful_benchmarks = [b for b in model_results['benchmarks'] if b.get('success')]
            
            if successful_benchmarks:
                avg_tokens_per_sec = sum(b['tokens_per_second'] for b in successful_benchmarks) / len(successful_benchmarks)
                avg_time_to_first_token = sum(b['time_to_first_token'] for b in successful_benchmarks) / len(successful_benchmarks)
                avg_memory = sum(b['memory_usage_mb'] for b in successful_benchmarks) / len(successful_benchmarks)
                
                model_results['summary'] = {
                    'average_tokens_per_second': avg_tokens_per_sec,
                    'average_time_to_first_token': avg_time_to_first_token,
                    'average_memory_usage_mb': avg_memory,
                    'successful_benchmarks': len(successful_benchmarks),
                    'total_benchmarks': len(test_prompts)
                }
            
            results[model] = model_results
        
        return {
            'timestamp': datetime.now().isoformat(),
            'ollama_available': True,
            'results': results
        }
    
    async def monitor_inference_performance(self, model: str, duration: int = 60) -> Dict:
        """Monitor inference performance over time"""
        if not self.ollama_available:
            return {'error': 'Ollama not available'}
        
        start_time = time.time()
        performance_data = []
        
        while time.time() - start_time < duration:
            # Run a quick inference
            result = await self.benchmark_model(
                model=model,
                prompt="Answer briefly: What is 2+2?",
                max_tokens=20
            )
            
            if result.get('success'):
                performance_data.append({
                    'timestamp': result['timestamp'],
                    'tokens_per_second': result['tokens_per_second'],
                    'time_to_first_token': result['time_to_first_token'],
                    'memory_usage_mb': result['memory_usage_mb']
                })
            
            await asyncio.sleep(5)  # Wait between tests
        
        # Calculate statistics
        if performance_data:
            avg_tps = sum(p['tokens_per_second'] for p in performance_data) / len(performance_data)
            avg_ttf = sum(p['time_to_first_token'] for p in performance_data) / len(performance_data)
            avg_mem = sum(p['memory_usage_mb'] for p in performance_data) / len(performance_data)
            
            return {
                'model': model,
                'duration_seconds': duration,
                'samples_count': len(performance_data),
                'average_tokens_per_second': avg_tps,
                'average_time_to_first_token': avg_ttf,
                'average_memory_usage_mb': avg_mem,
                'performance_data': performance_data,
                'timestamp': datetime.now().isoformat()
            }
        
        return {'error': 'No successful inference tests completed'}