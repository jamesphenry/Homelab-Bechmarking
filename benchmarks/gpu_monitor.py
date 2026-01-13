"""
GPU Monitoring utilities for benchmarking
"""
import asyncio
import subprocess
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class GPUMonitor:
    def __init__(self):
        self.gpu_available = self._check_gpu_available()
        self.gpu_count = self._get_gpu_count()
    
    def _check_gpu_available(self) -> bool:
        """Check if NVIDIA GPU is available"""
        try:
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _get_gpu_count(self) -> int:
        """Get number of GPUs"""
        if not self.gpu_available:
            return 0
        
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=count', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except:
            pass
        return 0
    
    async def get_gpu_metrics(self) -> Optional[Dict]:
        """Get current GPU metrics"""
        if not self.gpu_available:
            return None
        
        try:
            # Get detailed GPU information
            cmd = [
                'nvidia-smi',
                '--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw,clock.sm,clock.memory',
                '--format=csv,noheader,nounits'
            ]
            
            result = await asyncio.create_subprocess_shell(
                ' '.join(cmd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0 or not stdout:
                return None
            
            # Parse the CSV output
            lines = stdout.decode().strip().split('\n')
            metrics = []
            
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                
                parts = [part.strip() for part in line.split(',')]
                if len(parts) >= 8:
                    metrics.append({
                        'gpu_id': i,
                        'name': parts[0],
                        'temperature': float(parts[1]) if parts[1] != '[N/A]' else None,
                        'utilization': float(parts[2]) if parts[2] != '[N/A]' else None,
                        'memory_used': float(parts[3]) if parts[3] != '[N/A]' else None,
                        'memory_total': float(parts[4]) if parts[4] != '[N/A]' else None,
                        'power_draw': float(parts[5]) if parts[5] != '[N/A]' else None,
                        'clock_sm': float(parts[6]) if parts[6] != '[N/A]' else None,
                        'clock_memory': float(parts[7]) if parts[7] != '[N/A]' else None,
                        'timestamp': datetime.now().isoformat()
                    })
            
            return {
                'gpu_count': len(metrics),
                'gpus': metrics
            }
            
        except Exception as e:
            return None
    
    async def start_monitoring(self, callback, interval: float = 2.0):
        """Start continuous GPU monitoring"""
        if not self.gpu_available:
            return
        
        while True:
            metrics = await self.get_gpu_metrics()
            if metrics:
                await callback(metrics)
            await asyncio.sleep(interval)
    
    def get_gpu_info(self) -> Dict:
        """Get static GPU information"""
        if not self.gpu_available:
            return {'gpu_available': False}
        
        try:
            # Get comprehensive GPU info
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,driver_version,pci.bus_id,uuid', '--format=csv'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                gpus = []
                
                for line in lines:
                    if line.strip():
                        parts = [part.strip() for part in line.split(',')]
                        if len(parts) >= 4:
                            gpus.append({
                                'name': parts[0],
                                'driver_version': parts[1],
                                'pci_bus_id': parts[2],
                                'uuid': parts[3]
                            })
                
                return {
                    'gpu_available': True,
                    'gpu_count': len(gpus),
                    'gpus': gpus
                }
        except:
            pass
        
        return {'gpu_available': True, 'gpu_count': self.gpu_count}