import boto3
from datetime import date, timedelta, datetime
from botocore.exceptions import ClientError

def assume_role(role_arn, external_id):
    try:
        sts = boto3.client("sts")
        creds = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName="CostSession",
            ExternalId=str(external_id)  # Ensure it's string
        )["Credentials"]
        return boto3.client(
            "ce",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name="us-east-1"
        )
    except ClientError as e:
        print(f"STS AssumeRole Error: {e}")
        raise

def fetch_monthly_cost(ce):
    """Get current month's total spend"""
    try:
        today = date.today()
        start = today.replace(day=1)
        res = ce.get_cost_and_usage(
            TimePeriod={
                "Start": start.isoformat(),
                "End": today.isoformat(),
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
        if res["ResultsByTime"]:
            amount = float(res["ResultsByTime"][0]["Total"]["UnblendedCost"]["Amount"])
            return amount
        return 0.0
    except ClientError as e:
        print(f"Cost Explorer Error: {e}")
        return 0.0

def fetch_daily_costs(ce, days=90):
    """Get daily costs for last N days"""
    try:
        today = date.today()
        start = today - timedelta(days=days)
        res = ce.get_cost_and_usage(
            TimePeriod={
                "Start": start.isoformat(),
                "End": today.isoformat(),
            },
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
        )
        daily_costs = []
        for r in res["ResultsByTime"]:
            daily_costs.append({
                "date": r["TimePeriod"]["Start"],
                "amount": float(r["Total"]["UnblendedCost"]["Amount"]),
            })
        return daily_costs
    except ClientError as e:
        print(f"Daily Cost Error: {e}")
        return []

def fetch_total_historical_cost(ce):
    """Get total historical spend (all time)"""
    try:
        today = date.today()
        # Get start date from when account was likely created (3 years back max)
        start = today - timedelta(days=365*3)
        
        res = ce.get_cost_and_usage(
            TimePeriod={
                "Start": start.isoformat(),
                "End": today.isoformat(),
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
        
        total = 0.0
        for r in res["ResultsByTime"]:
            total += float(r["Total"]["UnblendedCost"]["Amount"])
        
        return total
    except ClientError as e:
        print(f"Historical Cost Error: {e}")
        return 0.0
    


def fetch_service_breakdown(ce, start_date, end_date):
    """Get cost breakdown by AWS service"""
    try:
        res = ce.get_cost_and_usage(
            TimePeriod={
                "Start": start_date.isoformat(),
                "End": end_date.isoformat(),
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[
                {
                    "Type": "DIMENSION",
                    "Key": "SERVICE"
                }
            ]
        )
        
        services = []
        if res["ResultsByTime"]:
            for group in res["ResultsByTime"][0].get("Groups", []):
                service_name = group["Keys"][0]
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                if amount > 0:  # Only include services with cost
                    services.append({
                        "service": service_name,
                        "amount": amount
                    })
        
        # Calculate percentages
        total = sum(s["amount"] for s in services)
        for service in services:
            service["percentage"] = (service["amount"] / total * 100) if total > 0 else 0
        
        # Sort by amount descending
        services.sort(key=lambda x: x["amount"], reverse=True)
        
        return services
        
    except ClientError as e:
        print(f"Service Breakdown Error: {e}")
        return []