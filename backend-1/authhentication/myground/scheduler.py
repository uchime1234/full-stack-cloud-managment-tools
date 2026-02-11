# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from datetime import datetime

from .tasks import (
    fetch_aws_costs,
    update_monthly_summary,
    update_cost_forecast,
    update_recent_daily_spend
)
from .models import AWSAccountConnection
from .resource_tracker import get_all_aws_resources, get_resource_usage_summary
from .cache_utils import ResourceCache

logger = logging.getLogger(__name__)

# --------------------------------------------------
# GLOBAL scheduler reference (CRITICAL)
# --------------------------------------------------
scheduler = None

# --------------------------------------------------
# Job functions
# --------------------------------------------------

def fetch_all_aws_costs():
    print("🔥 fetch_all_aws_costs triggered")
    
    accounts = AWSAccountConnection.objects.filter(is_active=True)
    print(f"🔥 Active AWS accounts: {accounts.count()}")
    
    for account in accounts:
        try:
            fetch_aws_costs(str(account.id))
            print(f"✅ Fetched AWS costs for {account.aws_account_id}")
        except Exception as e:
            print(f"❌ Error fetching AWS costs for {account.aws_account_id}: {e}")

def update_all_monthly_summaries():
    print("🔥 update_all_monthly_summaries triggered")
    
    accounts = AWSAccountConnection.objects.filter(is_active=True)
    print(f"🔥 Active AWS accounts: {accounts.count()}")
    
    for account in accounts:
        try:
            update_monthly_summary(str(account.id))
            print(f"✅ Updated monthly summary for {account.aws_account_id}")
        except Exception as e:
            print(f"❌ Error updating monthly summary for {account.aws_account_id}: {e}")

def update_all_cost_forecasts():
    print("🔥 update_all_cost_forecasts triggered")
    
    accounts = AWSAccountConnection.objects.filter(is_active=True)
    print(f"🔥 Active AWS accounts: {accounts.count()}")
    
    for account in accounts:
        try:
            update_cost_forecast(str(account.id))
            print(f"✅ Updated cost forecast for {account.aws_account_id}")
        except Exception as e:
            print(f"❌ Error updating cost forecast for {account.aws_account_id}: {e}")

def update_all_recent_spends():
    print("🔥 update_all_recent_spends triggered - 7 DAYS")
    
    accounts = AWSAccountConnection.objects.filter(is_active=True)
    print(f"🔥 Active AWS accounts: {accounts.count()}")
    
    for account in accounts:
        try:
            update_recent_daily_spend(str(account.id))
            print(f"✅ Updated recent 7-day spend for {account.aws_account_id}")
        except Exception as e:
            print(f"❌ Error updating recent spend for {account.aws_account_id}: {e}")

def fetch_all_aws_resources():
    """Fetch and cache AWS resources for all active accounts"""
    print("🔄 fetch_all_aws_resources triggered")
    
    accounts = AWSAccountConnection.objects.filter(is_active=True)
    print(f"🔄 Active AWS accounts for resource tracking: {accounts.count()}")
    
    for account in accounts:
        try:
            print(f"📊 Fetching resources for account: {account.aws_account_id}")
            
            # Fetch detailed resources
            resources = get_all_aws_resources(str(account.id), use_cache=False)
            if resources:
                print(f"✅ Fetched {resources['summary']['total_resources']} resources for {account.aws_account_id}")
                
                # Update last resource sync time
                account.last_resource_sync = datetime.now()
                account.save(update_fields=['last_resource_sync'])
            else:
                print(f"⚠️ No resources fetched for {account.aws_account_id}")
                
        except Exception as e:
            print(f"❌ Error fetching resources for {account.aws_account_id}: {e}")

# scheduler.py - Update the update_all_resource_summaries function

def update_all_resource_summaries():
    """Update resource summaries for all active accounts and save to database"""
    print("📈 update_all_resource_summaries triggered")
    accounts = AWSAccountConnection.objects.filter(is_active=True)
    print(f"📈 Active AWS accounts for resource summaries: {accounts.count()}")
    
    for account in accounts:
        try:
            print(f"📈 Updating resource summary for account: {account.aws_account_id}")
            
            # Fetch and cache resource summary (this will automatically save to DB)
            summary = get_resource_usage_summary(str(account.id), use_cache=False)
            
            if summary:
                print(f"✅ Updated resource summary for {account.aws_account_id}")
                print(f"   - Total resources: {summary.get('total_resources', 0)}")
                print(f"   - EC2 instances: {summary.get('ec2', {}).get('total', 0)}")
                print(f"   - S3 buckets: {summary.get('s3', {}).get('total_buckets', 0)}")
                
                # Update last resource sync time
                account.last_resource_sync = datetime.now()
                account.save(update_fields=['last_resource_sync'])
            else:
                print(f"⚠️ No resource summary for {account.aws_account_id}")
                
        except Exception as e:
            print(f"❌ Error updating resource summary for {account.aws_account_id}: {e}")

def refresh_all_cache():
    """Refresh all cache for all accounts"""
    print("🔄 refresh_all_cache triggered")
    
    accounts = AWSAccountConnection.objects.filter(is_active=True)
    print(f"🔄 Refreshing cache for {accounts.count()} accounts")
    
    for account in accounts:
        try:
            # Clear old cache
            ResourceCache.invalidate_account_cache(account.id)
            print(f"🧹 Cleared cache for {account.aws_account_id}")
        except Exception as e:
            print(f"❌ Error clearing cache for {account.aws_account_id}: {e}")

# --------------------------------------------------
# Scheduler startup
# --------------------------------------------------

def start_scheduler():
    global scheduler
    
    if scheduler and scheduler.running:
        print("⚠️ Scheduler already running — skipping")
        return
    
    scheduler = BackgroundScheduler(daemon=True)
    
    # 🔁 AWS Cost jobs (optimized intervals)
    scheduler.add_job(
        fetch_all_aws_costs,
        'interval',
        minutes=60,  # Fetch costs every hour
        id="fetch_aws_costs_job",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=30,
    )
    
    scheduler.add_job(
        update_all_monthly_summaries,
        'interval',
        minutes=120,  # Update monthly summary every 2 hours
        id="monthly_summary_job",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=30,
    )
    
    scheduler.add_job(
        update_all_cost_forecasts,
        'interval',
        minutes=180,  # Update forecasts every 3 hours
        id="cost_forecast_job",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=60,
    )
    
    scheduler.add_job(
        update_all_recent_spends,
        'interval',
        minutes=60,  # Update recent spends every hour
        id="recent_spends_job",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=60,
    )
    
    # 🔁 AWS Resource jobs (less frequent - resources don't change as often)
    scheduler.add_job(
        fetch_all_aws_resources,
        'interval',
        hours=6,  # Fetch resources every 6 hours
        id="fetch_aws_resources_job",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=300,
    )
    
    scheduler.add_job(
        update_all_resource_summaries,
        'interval',
        hours=6,  # Update summaries every 2 hours
        id="resource_summary_job",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=300,
    )
    
    # 🔁 Cache refresh job (keep cache fresh)
    scheduler.add_job(
        refresh_all_cache,
        'interval',
        hours=24,  # Refresh cache daily
        id="refresh_cache_job",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=600,
    )
    
    # 🚀 Start all jobs immediately on first run
    print("🚀 Running initial resource fetch...")
    try:
        fetch_all_aws_resources()
    except Exception as e:
        print(f"⚠️ Initial resource fetch failed: {e}")
    
    print("🚀 Running initial resource summary update...")
    try:
        update_all_resource_summaries()
    except Exception as e:
        print(f"⚠️ Initial resource summary update failed: {e}")
    
    scheduler.start()
    print("🕒 AWS scheduler started successfully!")
    print("   - Cost data: hourly")
    print("   - Resource data: every 6 hours")
    print("   - Cache refresh: daily")
    print("   - All data cached for fast API responses")