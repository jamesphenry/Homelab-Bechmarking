"""
Data parsing utilities for benchmark results
"""
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class BenchmarkDataParser:
    def __init__(self):
        pass
    
    def parse_sysbench_cpu(self, output: List[str]) -> Dict:
        """Parse sysbench CPU test output"""
        metrics = {}
        
        for line in output:
            line = line.strip()
            
            # Total events executed
            if "total number of events" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    metrics['total_events'] = int(match.group(1))
            
            # Events per second
            if "events per second" in line:
                match = re.search(r'events per second:\s*(\d+\.\d+)', line)
                if match:
                    metrics['events_per_second'] = float(match.group(1))
            
            # Total time
            if "total time:" in line and "s" in line:
                match = re.search(r'(\d+\.\d+)\s+s', line)
                if match:
                    metrics['total_time_seconds'] = float(match.group(1))
            
            # Event statistics
            if "min:" in line and "avg:" in line and "max:" in line:
                stats_match = re.search(r'min:\s+(\d+\.\d+)\s+avg:\s+(\d+\.\d+)\s+max:\s+(\d+\.\d+)', line)
                if stats_match:
                    metrics['event_time_min_ms'] = float(stats_match.group(1))
                    metrics['event_time_avg_ms'] = float(stats_match.group(2))
                    metrics['event_time_max_ms'] = float(stats_match.group(3))
            
            # Thread statistics
            if "threads fairness:" in line:
                if "events (avg/stddev)" in line:
                    events_match = re.search(r'events.*\(avg/stddev\):\s+(\d+\.\d+)/(\d+\.\d+)', line)
                    if events_match:
                        metrics['thread_events_avg'] = float(events_match.group(1))
                        metrics['thread_events_stddev'] = float(events_match.group(2))
                
                if "execution time (avg/stddev)" in line:
                    time_match = re.search(r'execution time.*\(avg/stddev\):\s+(\d+\.\d+)/(\d+\.\d+)', line)
                    if time_match:
                        metrics['thread_time_avg'] = float(time_match.group(1))
                        metrics['thread_time_stddev'] = float(time_match.group(2))
        
        return metrics
    
    def parse_sysbench_memory(self, output: List[str]) -> Dict:
        """Parse sysbench memory test output"""
        metrics = {}
        
        for line in output:
            line = line.strip()
            
            # Total operations
            if "total number of operations" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    metrics['total_operations'] = int(match.group(1))
            
            # Operations per second
            if "operations per second" in line:
                match = re.search(r'(\d+\.\d+)\s+operations per second', line)
                if match:
                    metrics['operations_per_second'] = float(match.group(1))
            
            # Memory transfer rates
            if "transferred" in line:
                # Look for read rate
                read_match = re.search(r'(\d+\.\d+)\s+MiB/sec', line)
                if read_match:
                    if 'read' in line.lower() or metrics.get('read_mib_sec') is None:
                        metrics['read_mib_sec'] = float(read_match.group(1))
                    else:
                        metrics['write_mib_sec'] = float(read_match.group(1))
            
            # Percentile statistics
            if "Percentile" in line and "ms" in line:
                percentile_match = re.findall(r'(\d+\.\d+)%', line)
                time_match = re.findall(r'(\d+\.\d+)\s+ms', line)
                
                if percentile_match and time_match:
                    for i, percent in enumerate(percentile_match):
                        if i < len(time_match):
                            metrics[f'percentile_{percent}_ms'] = float(time_match[i])
            
            # Summary statistics
            if "min:" in line and "avg:" in line and "max:" in line:
                stats_match = re.search(r'min:\s+(\d+\.\d+)\s+avg:\s+(\d+\.\d+)\s+max:\s+(\d+\.\d+)', line)
                if stats_match:
                    metrics['latency_min_ms'] = float(stats_match.group(1))
                    metrics['latency_avg_ms'] = float(stats_match.group(2))
                    metrics['latency_max_ms'] = float(stats_match.group(3))
        
        return metrics
    
    def parse_sysbench_disk(self, output: List[str]) -> Dict:
        """Parse sysbench disk test output"""
        metrics = {}
        
        for line in output:
            line = line.strip()
            
            # File operations
            if "total number of events" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    metrics['total_operations'] = int(match.group(1))
            
            # Operations per second
            if "operations per second" in line:
                match = re.search(r'(\d+\.\d+)\s+operations per second', line)
                if match:
                    metrics['operations_per_second'] = float(match.group(1))
            
            # Read/write performance
            if "read, MiB/s" in line:
                read_match = re.search(r'(\d+\.\d+)', line)
                if read_match:
                    metrics['read_mib_s'] = float(read_match.group(1))
            
            if "written, MiB/s" in line:
                write_match = re.search(r'(\d+\.\d+)', line)
                if write_match:
                    metrics['write_mib_s'] = float(write_match.group(1))
            
            # I/O statistics
            if "min:" in line and "avg:" in line and "max:" in line:
                stats_match = re.search(r'min:\s+(\d+\.\d+)\s+avg:\s+(\d+\.\d+)\s+max:\s+(\d+\.\d+)', line)
                if stats_match:
                    metrics['io_time_min_ms'] = float(stats_match.group(1))
                    metrics['io_time_avg_ms'] = float(stats_match.group(2))
                    metrics['io_time_max_ms'] = float(stats_match.group(3))
            
            # File size info
            if "File size" in line:
                size_match = re.search(r'(\d+\.\d+)\s+MiB', line)
                if size_match:
                    metrics['file_size_mib'] = float(size_match.group(1))
            
            # Block size info
            if "Block size" in line:
                block_match = re.search(r'(\d+)\s+bytes?', line)
                if block_match:
                    metrics['block_size_bytes'] = int(block_match.group(1))
        
        return metrics
    
    def parse_gpu_metrics(self, log_lines: List[str]) -> Dict:
        """Parse GPU monitoring metrics from log lines"""
        metrics = {
            'temperature_readings': [],
            'utilization_readings': [],
            'memory_used_readings': [],
            'memory_total_readings': [],
            'power_readings': [],
            'timestamps': [],
            'temperature_summary': {},
            'utilization_summary': {},
            'memory_summary': {}
        }
        
        for line in log_lines:
            if "Temperature:" in line:
                temp_match = re.search(r'Temperature:\s+(\d+)°C', line)
                if temp_match:
                    metrics['temperature_readings'].append(float(temp_match.group(1)))
                    
                    # Extract timestamp
                    timestamp_match = re.search(r'\[(.*?)\]', line)
                    if timestamp_match:
                        metrics['timestamps'].append(timestamp_match.group(1))
            
            if "Utilization:" in line:
                util_match = re.search(r'Utilization:\s+(\d+)%', line)
                if util_match:
                    metrics['utilization_readings'].append(float(util_match.group(1)))
            
            if "GPU Memory:" in line:
                mem_match = re.search(r'Memory:\s+(\d+)/(\d+)\s+MB', line)
                if mem_match:
                    metrics['memory_used_readings'].append(float(mem_match.group(1)))
                    metrics['memory_total_readings'].append(float(mem_match.group(2)))
        
        # Calculate summary statistics  
        metrics['temperature_summary'] = self._calculate_summary_stats(metrics['temperature_readings']) if metrics['temperature_readings'] else {}
        metrics['utilization_summary'] = self._calculate_summary_stats(metrics['utilization_readings']) if metrics['utilization_readings'] else {}
        metrics['memory_summary'] = self._calculate_summary_stats(metrics['memory_used_readings']) if metrics['memory_used_readings'] else {}
        
        return metrics
    
    def parse_ollama_benchmark(self, result: Dict) -> Dict:
        """Parse and structure Ollama benchmark results"""
        if not result.get('success'):
            return result
        
        parsed = {
            'model': result.get('model'),
            'prompt_length': len(result.get('prompt', '')),
            'output_length': len(result.get('output', '')),
            'total_time_seconds': result.get('total_time', 0),
            'time_to_first_token_ms': result.get('time_to_first_token', 0) * 1000,
            'tokens_per_second': result.get('tokens_per_second', 0),
            'memory_usage_mb': result.get('memory_usage_mb', 0),
            'success': result.get('success', False),
            'timestamp': result.get('timestamp')
        }
        
        # Calculate additional metrics
        if parsed['tokens_per_second'] > 0:
            parsed['ms_per_token'] = 1000 / parsed['tokens_per_second']
        
        if parsed['total_time_seconds'] > 0:
            parsed['output_tokens_per_second'] = parsed['output_length'] / parsed['total_time_seconds']
        
        return parsed
    
    def _calculate_summary_stats(self, values) -> Dict:
        """Calculate summary statistics for a list of values"""
        if not values:
            return {}
        
        values_sorted = sorted(values)
        count = len(values)
        
        return {
            'count': count,
            'min': min(values),
            'max': max(values),
            'mean': sum(values) / count,
            'median': values_sorted[count // 2] if count % 2 == 1 else (values_sorted[count // 2 - 1] + values_sorted[count // 2]) / 2,
            'p95': values_sorted[int(count * 0.95)] if count > 20 else max(values),
            'p99': values_sorted[int(count * 0.99)] if count > 100 else max(values)
        }
    
    def create_comprehensive_report(self, run_data: Dict) -> Dict:
        """Create a comprehensive benchmark report from run data"""
        report = {
            'run_name': run_data.get('name'),
            'timestamp': run_data.get('timestamp'),
            'summary': {},
            'detailed_results': {},
            'comparisons': {}
        }
        
        # CPU summary
        if run_data.get('cpu1Thread') and run_data.get('cpuAllThreads'):
            report['summary']['cpu'] = {
                'single_thread_score': run_data['cpu1Thread'],
                'multi_thread_score': run_data['cpuAllThreads'],
                'parallelization_efficiency': (run_data['cpuAllThreads'] / run_data['cpu1Thread']) if run_data['cpu1Thread'] > 0 else 0
            }
        
        # Memory summary
        if run_data.get('memory'):
            mem_data = run_data['memory']
            report['summary']['memory'] = {
                'read_mib_s': mem_data.get('read', 0),
                'write_mib_s': mem_data.get('write', 0),
                'total_mib_s': mem_data.get('read', 0) + mem_data.get('write', 0)
            }
        
        # Disk summary
        if run_data.get('disk'):
            disk_data = run_data['disk']
            report['summary']['disk'] = {
                'read_mib_s': disk_data.get('read', 0),
                'write_mib_s': disk_data.get('write', 0),
                'total_mib_s': disk_data.get('read', 0) + disk_data.get('write', 0)
            }
        
        # GPU summary
        if run_data.get('gpu'):
            gpu_data = run_data['gpu']
            if gpu_data.get('temperature_readings'):
                temp_summary = self._calculate_summary_stats(gpu_data['temperature_readings'])
                report['summary']['gpu'] = {
                    'temperature_avg_c': temp_summary.get('mean', 0),
                    'temperature_max_c': temp_summary.get('max', 0),
                    'utilization_avg_pct': 0  # Would be calculated if utilization data available
                }
        
        # Ollama summary
        if run_data.get('ollama'):
            ollama_data = run_data['ollama']
            report['summary']['ollama'] = {
                'tokens_per_second': ollama_data.get('tokens_per_sec', 0),
                'latency_ms': ollama_data.get('latency', 0) * 1000,
                'memory_usage_mb': ollama_data.get('memory_mb', 0)
            }
        
        return report