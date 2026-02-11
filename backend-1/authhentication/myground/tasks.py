from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import statistics
import math
from .cache_utils import ResourceCache
from django.db.models import Sum, Avg
from .models import (
    AWSAccountConnection, DailySpend, MonthlyCostSummary, RecentDailySpend
)

# Import AWS client functions
from .aws_client import assume_role, fetch_monthly_cost, fetch_daily_costs

def fetch_aws_costs(account_id):
    """Fetch REAL AWS costs from Cost Explorer API"""
    try:
        account = AWSAccountConnection.objects.get(id=account_id)
        print(f"🌐 Connecting to AWS for account: {account.aws_account_id}")
        
        # Clear old cache
        ResourceCache.invalidate_account_cache(account_id)
        
        # Get AWS client using STS AssumeRole
        try:
            from .aws_client import assume_role, fetch_daily_costs
            ce_client = assume_role(account.role_arn, str(account.external_id))
        except Exception as e:
            print(f"❌ Failed to assume role: {e}")
            return False
        
        # Fetch REAL daily costs from AWS
        aws_daily_costs = fetch_daily_costs(ce_client, days=100)
        
        if not aws_daily_costs:
            print("⚠️ No cost data returned from AWS")
            return False
        
        print(f"📊 Received {len(aws_daily_costs)} days of REAL data from AWS")
        
        # Process and save REAL AWS data
        for day_data in aws_daily_costs:
            date_str = day_data['date']
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            amount = Decimal(str(day_data['amount']))
            
            # Save REAL daily spend from AWS
            DailySpend.objects.update_or_create(
                account=account,
                date=date_obj,
                defaults={'amount': amount}
            )
        
        # Update sync time
        account.last_synced = timezone.now()
        account.save()

        ResourceCache.cache_resources(account_id, {
            'last_sync': account.last_synced,
            'status': 'success'
        })
        
        print(f"✅ Stored REAL AWS data for {account.aws_account_id}")
        print(f"   - Days processed: {len(aws_daily_costs)}")
        print(f"   - Last sync: {account.last_synced}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in fetch_aws_costs: {str(e)}")
        return False

def update_monthly_summary(account_id):
    """Update monthly summary with real data"""
    try:
        account = AWSAccountConnection.objects.get(id=account_id)
        today = timezone.now().date()
        
        # Get current month data
        current_month_start = today.replace(day=1)
        current_month_spends = DailySpend.objects.filter(
            account=account,
            date__gte=current_month_start
        )
        
        if not current_month_spends.exists():
            print(f"⚠️ No current month spends found for {account.aws_account_id}")
            MonthlyCostSummary.objects.update_or_create(
                account=account,
                defaults={
                    "total_spend": Decimal("0"),
                    "daily_average": Decimal("0"),
                    "monthly_change": Decimal("0"),
                }
            )
            return True
        
        # Calculate REAL totals from database
        total_spend = sum([spend.amount for spend in current_month_spends])
        daily_average = total_spend / len(current_month_spends) if current_month_spends else Decimal('0')
        
        # Get last month for comparison
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        last_month_spends = DailySpend.objects.filter(
            account=account,
            date__gte=last_month_start,
            date__lt=current_month_start
        )
        
        # Calculate monthly change based on REAL data
        monthly_change = None
        if last_month_spends.exists():
            last_month_total = sum([spend.amount for spend in last_month_spends])
            if last_month_total > 0:
                monthly_change = ((float(total_spend) - float(last_month_total)) / float(last_month_total)) * 100
        
        # Create or update monthly summary with REAL data
        MonthlyCostSummary.objects.update_or_create(
            account=account,
            defaults={
                'total_spend': total_spend,
                'daily_average': daily_average,
                'monthly_change': monthly_change
            }
        )
        
        print(f"✅ Updated monthly summary for {account.aws_account_id}")
        print(f"   - Current month: ${total_spend}")
        print(f"   - Daily average: ${daily_average}")
        
        return True
    except Exception as e:
        print(f"❌ Error in update_monthly_summary: {str(e)}")
        return False

def update_cost_forecast(account_id):
    """Update cost forecast based on REAL data"""
    try:
        account = AWSAccountConnection.objects.get(id=account_id)
        today = timezone.now().date()
        
        # Get last 30 days of REAL data
        start_date = today - timedelta(days=30)
        daily_spends = DailySpend.objects.filter(
            account=account,
            date__gte=start_date
        ).order_by('date')
        
        if not daily_spends.exists() or len(daily_spends) < 7:
            print(f"⚠️ Not enough data for forecast for {account.aws_account_id}")
            return False
        
        # Convert to REAL amounts list
        amounts = [float(spend.amount) for spend in daily_spends]
        
        # Simple moving average for forecast
        def moving_average(data, window=7):
            if len(data) < window:
                return data[-1] if data else 0
            return sum(data[-window:]) / window
        
        # Calculate forecasts based on REAL data
        forecast_7d = moving_average(amounts, 7) * 7  # Weekly forecast
        forecast_30d = moving_average(amounts, 7) * 30  # Monthly forecast
        
        # Save forecasts
        monthly_summary = MonthlyCostSummary.objects.filter(account=account).first()
        if monthly_summary:
            monthly_summary.forecast_7d = Decimal(str(forecast_7d))
            monthly_summary.forecast_30d = Decimal(str(forecast_30d))
            monthly_summary.save()
        
        print(f"✅ Updated cost forecast for {account.aws_account_id}")
        print(f"   - 7-day forecast: ${forecast_7d:.2f}")
        print(f"   - 30-day forecast: ${forecast_30d:.2f}")
        
        return True
    except Exception as e:
        print(f"❌ Error in update_cost_forecast: {str(e)}")
        return False

def update_recent_daily_spend(account_id):
    """Update recent 7 days for bar chart with REAL data"""
    try:
        account = AWSAccountConnection.objects.get(id=account_id)
        today = timezone.now().date()
        
        # Get last 7 days of REAL data (including today)
        daily_spends = []
        date_labels = []
        
        # Get spends for last 7 days (6 days ago to today)
        for i in range(6, -1, -1):  # From 6 days ago to today
            target_date = today - timedelta(days=i)
            
            # Find spend for this date
            spend = DailySpend.objects.filter(
                account=account,
                date=target_date
            ).first()
            
            amount = spend.amount if spend else Decimal('0')
            daily_spends.append(amount)
            date_labels.append(target_date.strftime('%a'))  # Short day name
        
        # Create or update RecentDailySpend with REAL data
        RecentDailySpend.objects.update_or_create(
            account=account,
            defaults={
                'day_1': daily_spends[0] if len(daily_spends) > 0 else Decimal('0'),
                'day_2': daily_spends[1] if len(daily_spends) > 1 else Decimal('0'),
                'day_3': daily_spends[2] if len(daily_spends) > 2 else Decimal('0'),
                'day_4': daily_spends[3] if len(daily_spends) > 3 else Decimal('0'),
                'day_5': daily_spends[4] if len(daily_spends) > 4 else Decimal('0'),
                'day_6': daily_spends[5] if len(daily_spends) > 5 else Decimal('0'),
                'day_7': daily_spends[6] if len(daily_spends) > 6 else Decimal('0'),
                'date_labels': date_labels
            }
        )
        
        print(f"✅ Updated 7-day recent spend for account {account.aws_account_id}")
        return True
    except Exception as e:
        print(f"❌ Error in update_recent_daily_spend: {str(e)}")
        return False