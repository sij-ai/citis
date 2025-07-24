"""
Django management command to update existing users with new quota system.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Update existing users with new quota system and student detection'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        users = User.objects.all()
        updated_count = 0
        student_count = 0
        
        for user in users:
            changes = []
            
            # Check and update student status
            old_student_status = user.is_student
            is_academic = user.is_academic_email(user.email)
            
            if is_academic != old_student_status:
                changes.append(f"student: {old_student_status} -> {is_academic}")
                if not dry_run:
                    user.is_student = is_academic
                    if is_academic:
                        user.student_verified_at = user.created_at
                        student_count += 1
            
            # Update plan quotas if user is on default values or premium
            should_update_quotas = False
            
            # Check if user needs plan update based on premium status
            if user.is_premium and user.current_plan == 'free':
                changes.append(f"plan: {user.current_plan} -> professional")
                if not dry_run:
                    user.current_plan = 'professional'
                should_update_quotas = True
            elif not user.is_premium and user.current_plan != 'free':
                changes.append(f"plan: {user.current_plan} -> free")
                if not dry_run:
                    user.current_plan = 'free'
                should_update_quotas = True
            
            # Update quotas to match current plan
            if should_update_quotas:
                if not dry_run:
                    user.update_plan_quotas()
                changes.append("quotas updated for plan")
            
            if changes:
                self.stdout.write(
                    f"User {user.email}: {', '.join(changes)}"
                )
                if not dry_run:
                    user.save(update_fields=[
                        'is_student', 'student_verified_at', 'current_plan'
                    ])
                updated_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'DRY RUN: Would update {updated_count} users, '
                    f'{student_count} would become students'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Updated {updated_count} users, '
                    f'{student_count} detected as students'
                )
            ) 