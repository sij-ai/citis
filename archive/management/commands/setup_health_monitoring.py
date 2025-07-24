"""
Django management command to set up periodic health monitoring tasks.
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule, IntervalSchedule
import json


class Command(BaseCommand):
    help = 'Set up periodic health monitoring tasks for different plan tiers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Remove existing health monitoring tasks before creating new ones',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Removing existing health monitoring tasks...')
            PeriodicTask.objects.filter(
                name__startswith='health_monitoring_'
            ).delete()
            self.stdout.write(
                self.style.SUCCESS('Removed existing health monitoring tasks')
            )

        # Create schedule objects
        schedules = self._create_schedules()
        
        # Create periodic tasks for each plan tier and check type
        tasks_created = 0
        
        # Free tier - Link health checks every day
        if self._create_task(
            name='health_monitoring_free_link_health',
            task='archive.tasks.bulk_health_monitoring_task',
            schedule=schedules['daily'],
            kwargs={'plan_filter': 'free', 'check_type': 'link_health'},
            description='Daily link health checks for free tier users'
        ):
            tasks_created += 1
        
        # Professional tier - Link health checks every 5 minutes
        if self._create_task(
            name='health_monitoring_professional_link_health',
            task='archive.tasks.bulk_health_monitoring_task',
            schedule=schedules['5_minutes'],
            kwargs={'plan_filter': 'professional', 'check_type': 'link_health'},
            description='5-minute link health checks for professional tier users'
        ):
            tasks_created += 1
        
        # Professional tier - Content integrity scans every hour
        if self._create_task(
            name='health_monitoring_professional_content_integrity',
            task='archive.tasks.bulk_health_monitoring_task',
            schedule=schedules['hourly'],
            kwargs={'plan_filter': 'professional', 'check_type': 'content_integrity'},
            description='Hourly content integrity scans for professional tier users'
        ):
            tasks_created += 1
        
        # Sovereign tier - Link health checks every minute (near real-time)
        if self._create_task(
            name='health_monitoring_sovereign_link_health',
            task='archive.tasks.bulk_health_monitoring_task',
            schedule=schedules['1_minute'],
            kwargs={'plan_filter': 'sovereign', 'check_type': 'link_health'},
            description='Real-time link health checks for sovereign tier users'
        ):
            tasks_created += 1
        
        # Sovereign tier - Content integrity scans every 5 minutes
        if self._create_task(
            name='health_monitoring_sovereign_content_integrity',
            task='archive.tasks.bulk_health_monitoring_task',
            schedule=schedules['5_minutes'],
            kwargs={'plan_filter': 'sovereign', 'check_type': 'content_integrity'},
            description='5-minute content integrity scans for sovereign tier users'
        ):
            tasks_created += 1
        
        # Cleanup task - daily cleanup of failed archives
        if self._create_task(
            name='cleanup_failed_archives',
            task='archive.tasks.cleanup_failed_archives_task',
            schedule=schedules['daily'],
            kwargs={},
            description='Daily cleanup of failed archive attempts'
        ):
            tasks_created += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {tasks_created} periodic health monitoring tasks')
        )
        
        # Show current status
        self._show_task_status()

    def _create_schedules(self):
        """Create and return schedule objects for different intervals."""
        schedules = {}
        
        # 1 minute interval
        schedules['1_minute'], _ = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.MINUTES
        )
        
        # 5 minute interval  
        schedules['5_minutes'], _ = IntervalSchedule.objects.get_or_create(
            every=5,
            period=IntervalSchedule.MINUTES
        )
        
        # Hourly interval
        schedules['hourly'], _ = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.HOURS
        )
        
        # Daily interval (at 2 AM)
        schedules['daily'], _ = CrontabSchedule.objects.get_or_create(
            minute=0,
            hour=2,
            day_of_week='*',
            day_of_month='*',
            month_of_year='*'
        )
        
        return schedules

    def _create_task(self, name, task, schedule, kwargs, description):
        """Create a periodic task if it doesn't exist."""
        task_obj, created = PeriodicTask.objects.get_or_create(
            name=name,
            defaults={
                'task': task,
                'interval': schedule if hasattr(schedule, 'every') else None,
                'crontab': schedule if hasattr(schedule, 'minute') else None,
                'kwargs': json.dumps(kwargs),
                'description': description,
                'enabled': True
            }
        )
        
        if created:
            self.stdout.write(f'Created task: {name}')
        else:
            self.stdout.write(f'Task already exists: {name}')
        
        return created

    def _show_task_status(self):
        """Show status of all health monitoring tasks."""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Health Monitoring Task Status:')
        self.stdout.write('='*50)
        
        tasks = PeriodicTask.objects.filter(
            name__startswith='health_monitoring_'
        ).order_by('name')
        
        for task in tasks:
            status = 'ENABLED' if task.enabled else 'DISABLED'
            if task.interval:
                schedule_info = f"every {task.interval.every} {task.interval.period}"
            elif task.crontab:
                schedule_info = f"daily at {task.crontab.hour:02d}:{task.crontab.minute:02d}"
            else:
                schedule_info = "unknown schedule"
            
            self.stdout.write(f'{task.name:<50} {status:<10} {schedule_info}')
        
        # Also show cleanup task
        cleanup_tasks = PeriodicTask.objects.filter(name='cleanup_failed_archives')
        for task in cleanup_tasks:
            status = 'ENABLED' if task.enabled else 'DISABLED'
            self.stdout.write(f'{task.name:<50} {status:<10} daily cleanup')
        
        self.stdout.write('\n' + 'To start monitoring, run: python manage_celery.py beat')
        self.stdout.write('='*50) 