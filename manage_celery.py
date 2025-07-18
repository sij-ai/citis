#!/usr/bin/env python
"""
Helper script for managing Celery workers and beat scheduler.
"""
import os
import sys
import subprocess
from pathlib import Path

# Add project directory to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'citis.settings')


def start_worker(queue=None, concurrency=2):
    """Start a Celery worker"""
    cmd = ['celery', '-A', 'citis', 'worker', '--loglevel=info', f'--concurrency={concurrency}']
    
    if queue:
        cmd.extend(['-Q', queue])
    
    print(f"Starting Celery worker: {' '.join(cmd)}")
    subprocess.run(cmd)


def start_beat():
    """Start Celery beat scheduler"""
    cmd = ['celery', '-A', 'citis', 'beat', '--loglevel=info', '--scheduler', 'django_celery_beat.schedulers:DatabaseScheduler']
    
    print(f"Starting Celery beat: {' '.join(cmd)}")
    subprocess.run(cmd)


def start_flower():
    """Start Flower monitoring"""
    cmd = ['celery', '-A', 'citis', 'flower']
    
    print(f"Starting Flower monitoring: {' '.join(cmd)}")
    subprocess.run(cmd)


def show_status():
    """Show Celery worker status"""
    cmd = ['celery', '-A', 'citis', 'inspect', 'active']
    subprocess.run(cmd)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage Celery workers for citis')
    parser.add_argument('command', choices=['worker', 'beat', 'flower', 'status'], 
                       help='Command to run')
    parser.add_argument('--queue', help='Queue name for worker (archive, assets, analytics)')
    parser.add_argument('--concurrency', type=int, default=2, help='Worker concurrency')
    
    args = parser.parse_args()
    
    if args.command == 'worker':
        start_worker(args.queue, args.concurrency)
    elif args.command == 'beat':
        start_beat()
    elif args.command == 'flower':
        start_flower()
    elif args.command == 'status':
        show_status() 