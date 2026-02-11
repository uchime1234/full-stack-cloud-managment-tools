from django.db import models
from django.contrib.auth.models import User
import pyotp
import uuid
from django.utils import timezone

# Your existing VerificationCode model
class VerificationCode(models.Model):
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.email}"

# Your existing MFA models
class MFAConfiguration(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mfa_config')
    secret_key = models.CharField(max_length=32, unique=True)
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"MFA Config for {self.user.username}"
    
    def get_totp_uri(self, issuer_name="Cloud Management"):
        totp = pyotp.TOTP(self.secret_key)
        return totp.provisioning_uri(
            name=self.user.email,
            issuer_name=issuer_name
        )
    
    def verify_code(self, code):
        totp = pyotp.TOTP(self.secret_key)
        return totp.verify(code)

class BackupCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='backup_codes')
    code = models.CharField(max_length=25, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Backup code for {self.user.username}"

class MFALog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mfa_logs')
    action = models.CharField(max_length=50)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

# Your existing AWS models (with minor enhancements)
class AWSAccountConnection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="aws_accounts")
    aws_account_id = models.CharField(max_length=20)
    role_arn = models.CharField(max_length=255)
    external_id = models.UUIDField(default=uuid.uuid4)  # Added default
    is_active = models.BooleanField(default=True)  # Added field
    created_at = models.DateTimeField(auto_now_add=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    last_resource_sync = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'aws_account_id']  # Added unique constraint
    
    def __str__(self):
        return f"{self.user.username} - {self.aws_account_id}"

class DailySpend(models.Model):
    account = models.ForeignKey(AWSAccountConnection, on_delete=models.CASCADE, related_name='daily_spends')
    date = models.DateField()
    # Increase decimal_places to handle AWS precision
    amount = models.DecimalField(max_digits=15, decimal_places=9)  # Changed from 12,2 to 15,9
    
    class Meta:
        unique_together = ("account", "date")
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.account.aws_account_id} - {self.date}: ${self.amount}"

class MonthlyCostSummary(models.Model):
    account = models.OneToOneField(AWSAccountConnection, on_delete=models.CASCADE, related_name='monthly_summary')
    # Increase decimal_places
    total_spend = models.DecimalField(max_digits=15, decimal_places=9, default=0)  # Changed
    daily_average = models.DecimalField(max_digits=15, decimal_places=9, default=0)  # Changed
    forecast_7d = models.DecimalField(max_digits=15, decimal_places=9, null=True, blank=True)  # Changed
    forecast_30d = models.DecimalField(max_digits=15, decimal_places=9, null=True, blank=True)  # Changed
    monthly_change = models.DecimalField(max_digits=15, decimal_places=9, null=True, blank=True)  # Changed
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Monthly Summary for {self.account.aws_account_id}"

class RecentDailySpend(models.Model):
    account = models.OneToOneField(AWSAccountConnection, on_delete=models.CASCADE, related_name='recent_spends')
    # Increase decimal_places for all day fields
    day_1 = models.DecimalField(max_digits=15, decimal_places=9, default=0)  # Changed
    day_2 = models.DecimalField(max_digits=15, decimal_places=9, default=0)  # Changed
    day_3 = models.DecimalField(max_digits=15, decimal_places=9, default=0)  # Changed
    day_4 = models.DecimalField(max_digits=15, decimal_places=9, default=0)  # Changed
    day_5 = models.DecimalField(max_digits=15, decimal_places=9, default=0)  # Changed
    day_6 = models.DecimalField(max_digits=15, decimal_places=9, default=0)  # Changed
    day_7 = models.DecimalField(max_digits=15, decimal_places=9, default=0)  # Changed
    date_labels = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_daily_spend_array(self):
        """Return array for frontend bar chart (7 days)"""
        return [
            {'date': self.date_labels[0] if len(self.date_labels) > 0 else '', 'amount': round(float(self.day_1), 2)},
            {'date': self.date_labels[1] if len(self.date_labels) > 1 else '', 'amount': round(float(self.day_2), 2)},
            {'date': self.date_labels[2] if len(self.date_labels) > 2 else '', 'amount': round(float(self.day_3), 2)},
            {'date': self.date_labels[3] if len(self.date_labels) > 3 else '', 'amount': round(float(self.day_4), 2)},
            {'date': self.date_labels[4] if len(self.date_labels) > 4 else '', 'amount': round(float(self.day_5), 2)},
            {'date': self.date_labels[5] if len(self.date_labels) > 5 else '', 'amount': round(float(self.day_6), 2)},
            {'date': self.date_labels[6] if len(self.date_labels) > 6 else '', 'amount': round(float(self.day_7), 2)},
        ]



class ResourceSummary(models.Model):
    """Store resource summary data for each AWS account"""
    account = models.OneToOneField(
        AWSAccountConnection, 
        on_delete=models.CASCADE, 
        related_name='resource_summary'
    )
    
    # Resource counts
    total_resources = models.IntegerField(default=0)
    ec2_total = models.IntegerField(default=0)
    ec2_running = models.IntegerField(default=0)
    ec2_stopped = models.IntegerField(default=0)
    ec2_avg_running_hours = models.DecimalField(max_digits=10, decimal_places=1, default=0)
    
    s3_total_buckets = models.IntegerField(default=0)
    s3_avg_age_days = models.DecimalField(max_digits=10, decimal_places=1, default=0)
    
    lambda_total_functions = models.IntegerField(default=0)
    rds_total_instances = models.IntegerField(default=0)
    load_balancers_total = models.IntegerField(default=0)
    cloudfront_total = models.IntegerField(default=0)
    elasticache_total = models.IntegerField(default=0)
    eks_total = models.IntegerField(default=0)
    api_gateway_total = models.IntegerField(default=0)
    dynamodb_total = models.IntegerField(default=0)
    sqs_total = models.IntegerField(default=0)
    sns_total = models.IntegerField(default=0)
    
    # Additional metrics
    permissions_issues = models.JSONField(default=list, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-last_updated']
    
    def __str__(self):
        return f"Resource Summary for {self.account.aws_account_id}"
    
    def to_dict(self):
        """Convert to dictionary format for API"""
        return {
            'total_resources': self.total_resources,
            'ec2': {
                'total': self.ec2_total,
                'running': self.ec2_running,
                'stopped': self.ec2_stopped,
                'avg_running_hours': float(self.ec2_avg_running_hours)
            },
            's3': {
                'total_buckets': self.s3_total_buckets,
                'avg_age_days': float(self.s3_avg_age_days)
            },
            'lambda': {
                'total_functions': self.lambda_total_functions
            },
            'rds': {
                'total_instances': self.rds_total_instances
            },
            'load_balancers': {
                'total': self.load_balancers_total
            },
            'cloudfront': {
                'total': self.cloudfront_total
            },
            'elasticache': {
                'total': self.elasticache_total
            },
            'eks': {
                'total': self.eks_total
            },
            'api_gateway': {
                'total': self.api_gateway_total
            },
            'dynamodb': {
                'total': self.dynamodb_total
            },
            'sqs': {
                'total': self.sqs_total
            },
            'sns': {
                'total': self.sns_total
            },
            'permissions_issues': self.permissions_issues,
            'last_updated': self.last_updated.isoformat(),
            'cached': False
        }


from django.db import models
from django.contrib.postgres.fields import JSONField  # Use JSONField for PostgreSQL
from django.utils import timezone


class LowLevelServiceCategory(models.Model):
    """Service categories (Compute, Storage, Networking, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    key = models.CharField(max_length=50, unique=True)  # 'ec2', 's3', etc.
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Low level service categories"
    
    def __str__(self):
        return self.name

class LowLevelServiceDefinition(models.Model):
    """Definition of a low-level service from LOW_LEVEL_SERVICES"""
    service_id = models.CharField(max_length=100, unique=True)  # 'internet_gateway', 'nat_gateway'
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(LowLevelServiceCategory, on_delete=models.CASCADE, related_name='services')
    
    # Pricing fields - all nullable since not all services have all price types
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_gb = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_gb_month = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_gb_second = models.DecimalField(max_digits=10, decimal_places=10, null=True, blank=True)
    price_per_million = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_million_units = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_10k = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_thousand = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_iops_hour = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_iops_month = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_vcpu_hour = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_dpu_hour = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_connection_minute = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    price_per_month = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_year = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_device = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_sms = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_image = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    price_per_scan = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    
    # Unit description
    unit = models.CharField(max_length=200, help_text="Description of pricing unit")
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.category.key} - {self.name}"

class LowLevelServiceResource(models.Model):
    """Discovered resources in AWS accounts"""
    account = models.ForeignKey(AWSAccountConnection, on_delete=models.CASCADE, related_name='low_level_resources')
    service_definition = models.ForeignKey(LowLevelServiceDefinition, on_delete=models.CASCADE)
    
    # Resource identification
    resource_id = models.CharField(max_length=500)  # AWS resource ID
    resource_name = models.CharField(max_length=500, blank=True)
    region = models.CharField(max_length=50)
    
    # Quantities
    count = models.IntegerField(default=1)
    
    # Cost calculation
    estimated_monthly_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Detailed metadata
    details = models.JSONField(default=dict, blank=True)
    
    # Discovery metadata
    discovered_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['account', 'service_definition', 'resource_id', 'region']
        indexes = [
            models.Index(fields=['account', 'region']),
            models.Index(fields=['account', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.service_definition.name} - {self.resource_id}"

class LowLevelServiceSnapshot(models.Model):
    """Point-in-time snapshots of all low-level services for an account"""
    account = models.ForeignKey(AWSAccountConnection, on_delete=models.CASCADE, related_name='low_level_snapshots')
    
    # Summary data
    total_services = models.IntegerField()
    estimated_monthly_cost = models.DecimalField(max_digits=14, decimal_places=2)
    unique_service_types = models.IntegerField()
    unique_services_discovered = models.IntegerField()
    regions_scanned = models.JSONField(default=list)
    
    # Full snapshot data
    snapshot_data = models.JSONField()  # Store the complete response
    
    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    scan_duration_seconds = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        get_latest_by = 'created_at'
    
    def __str__(self):
        return f"Snapshot {self.account.id} - {self.created_at}"

class LowLevelServiceCostHistory(models.Model):
    """Historical cost tracking for trend analysis"""
    account = models.ForeignKey(AWSAccountConnection, on_delete=models.CASCADE, related_name='low_level_cost_history')
    service_definition = models.ForeignKey(LowLevelServiceDefinition, on_delete=models.CASCADE)
    
    date = models.DateField()
    monthly_cost = models.DecimalField(max_digits=12, decimal_places=2)
    resource_count = models.IntegerField()
    
    # Breakdown by region
    region_breakdown = models.JSONField(default=dict)
    
    class Meta:
        unique_together = ['account', 'service_definition', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.account.id} - {self.service_definition.name} - {self.date}"