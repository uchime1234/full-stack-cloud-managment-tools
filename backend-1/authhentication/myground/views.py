from django.shortcuts import render
from django.shortcuts import redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.models import User, auth
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework import status
import requests
import base64
from django.core.mail import send_mail
import random
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework import status
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import boto3
from django.db import transaction
import time
import json
from .serializers import AWSAccountConnectionSerializer, CostAnalyticsSerializer, ResourceSummarySerializer
from .models import VerificationCode, MFAConfiguration, BackupCode, MFALog, AWSAccountConnection, MonthlyCostSummary, DailySpend, RecentDailySpend, ResourceSummary, LowLevelServiceSnapshot, LowLevelServiceCategory, LowLevelServiceCostHistory, LowLevelServiceDefinition, LowLevelServiceResource 
import uuid
from .resource_tracker import get_all_paid_resources, analyze_cost_impact, COST_CATEGORIES
from .low_level_tracker import discover_global_services, discover_low_level_services, discover_region_services  

# AWS Client imports
from .aws_client import assume_role, fetch_monthly_cost, fetch_daily_costs, fetch_service_breakdown

# Tasks imports
from .tasks import (
    fetch_aws_costs, update_monthly_summary, 
    update_cost_forecast, update_recent_daily_spend
)

# Serializers imports
from .serializers import UserSerializer

# MFA Utils imports
from .utils.mfa_utils import (
    generate_secret_key, 
    generate_qr_code, 
    generate_backup_codes,
    verify_totp_code,
    check_rate_limit
)

# Resource tracker imports
from .resource_tracker import get_aws_resources, get_resource_usage_summary

# Rest Framework imports
from rest_framework import viewsets, generics
from rest_framework.decorators import action

# Create your views here.

@api_view(["GET", 'POST'])
def register_user(request):
    if request.method == "POST":
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        verification_code = request.data.get('verification_code')
        
        if not all([username, email, password]):
            return Response({"error": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=email).exists():
            return Response({"error":'Email already exists'}, status=400)
        
        if User.objects.filter(username=username).exists():
            return Response({"error":'Username already exists'}, status=400) 
        
        if not verification_code:
            return send_verification_code(email)
        
        # Call the updated verify_and_register function
        return verify_and_register(username, email, password, verification_code)
    
    elif request.method == "GET":
        # FIXED: Serialize the queryset properly
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)  # Serialize the queryset
        return Response(serializer.data)  # Now this is correct!
    

def send_verification_code(email):
    """Helper function to send verification code"""
    # Generate a 6-digit code
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    # Save the code (without creating a user yet)
    verification_code, created = VerificationCode.objects.update_or_create(
        email=email,  # We use email as identifier since user doesn't exist yet
        defaults={'code': code, 'is_used': False}
    )
    
    # Send email (using Django's built-in email backend)
    subject = 'Your Account Verification Code'
    message = f'Your verification code is: {code}'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [email]
    
    try:
        send_mail(subject, message, email_from, recipient_list)
        return Response({
            "message": "Verification code sent to your email",
            "next_step": "Submit the code to complete registration"
        }, status=status.HTTP_200_OK)
    except Exception as e:
        print("Email send failed:", str(e))
        return Response({"error": f"Failed to send verification code: {str(e)}"}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def verify_and_register(username, email, password, verification_code):
    """Helper function to verify code and register user"""
    try:
        # Check verification code
        verification = VerificationCode.objects.get(
            email=email,
            code=verification_code,
            is_used=False
        )
    except VerificationCode.DoesNotExist:
        return Response({"error": "Invalid or expired verification code"}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # Mark code as used
    verification.is_used = True
    verification.save()
    
    # Create the user
    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Create token for immediate authentication
        token, _ = Token.objects.get_or_create(user=user)
        
        # Generate MFA secret key immediately after registration (disabled by default)
        secret_key = generate_secret_key()
        MFAConfiguration.objects.create(user=user, secret_key=secret_key, is_enabled=False)
        
        return Response({
            "message": "Registration successful",
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "token": token.key,  # Return token for immediate auth
            "next_step": "mfa_setup"
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({"error": f"Failed to create user: {str(e)}"}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# myground/views.py (update login_user function)
@api_view(['POST'])
def login_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    mfa_code = request.data.get('mfa_code')  # Optional for MFA
    
    user = auth.authenticate(username=username, password=password)
    
    if user is not None:
        # Check if MFA is enabled
        try:
            mfa_config = MFAConfiguration.objects.get(user=user, is_enabled=True)
            
            if not mfa_code:
                # MFA is enabled but no code provided
                return Response({
                    "mfa_required": True,
                    "user_id": user.id,
                    "message": "MFA code required"
                }, status=status.HTTP_200_OK)
            
            # Verify MFA code
            if not verify_totp_code(mfa_config.secret_key, mfa_code):
                return Response({
                    "error": "Invalid MFA code"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except MFAConfiguration.DoesNotExist:
            pass  # MFA not enabled
        
        # Create token and return success
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,  
            "message": 'Login successful',
            "user_id": user.id,
            "username": user.username,
            "email": user.email
        }, status=status.HTTP_200_OK)
    else:
        return Response({"error":'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# TOKEN-BASED MFA ENDPOINTS (for post-registration setup)
# ============================================================

@api_view(['GET'])
def mfa_setup_init_token(request):
    """
    Initialize MFA setup using token from registration
    Does NOT require @permission_classes([IsAuthenticated])
    """
    # Get token from query parameter or header
    token = request.query_params.get('token') or request.headers.get('Authorization')
    
    if not token:
        return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Clean token if it's in "Token <key>" format
    if isinstance(token, str) and token.startswith('Token '):
        token = token[6:]
    
    try:
        # Find user by token
        token_obj = Token.objects.get(key=token)
        user = token_obj.user
        
        # Get or create MFA configuration
        try:
            mfa_config = MFAConfiguration.objects.get(user=user)
            if mfa_config.is_enabled:
                return Response({
                    "error": "MFA is already enabled for this account"
                }, status=status.HTTP_400_BAD_REQUEST)
            secret_key = mfa_config.secret_key
        except MFAConfiguration.DoesNotExist:
            # Generate new secret key
            secret_key = generate_secret_key()
            MFAConfiguration.objects.create(user=user, secret_key=secret_key, is_enabled=False)
            mfa_config = MFAConfiguration.objects.get(user=user)
        
        # Generate QR code
        qr_code_data = generate_qr_code(secret_key, user.email)
        
        return Response({
            "user_id": user.id,
            "username": user.username,
            "secret_key": secret_key,
            "qr_code": qr_code_data,
            "message": "Scan QR code with authenticator app"
        }, status=status.HTTP_200_OK)
        
    except Token.DoesNotExist:
        return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return Response({"error": f"Server error: {str(e)}"}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def mfa_enable_token(request):
    """
    Enable MFA using token from registration
    """
    token = request.data.get('token') or request.query_params.get('token')
    code = request.data.get('code')
    
    if not all([token, code]):
        return Response({"error": "Token and verification code are required"}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # Clean token if needed
    if isinstance(token, str) and token.startswith('Token '):
        token = token[6:]
    
    try:
        # Find user by token
        token_obj = Token.objects.get(key=token)
        user = token_obj.user
        
        # Check rate limit
        if not check_rate_limit(user.id, 'mfa_enable', limit=3, window=300):
            return Response({"error": "Too many attempts. Please try again later."},
                           status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        mfa_config = MFAConfiguration.objects.get(user=user)
        
        # Verify the code
        if not verify_totp_code(mfa_config.secret_key, code):
            return Response({"error": "Invalid verification code"}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Enable MFA
        mfa_config.is_enabled = True
        mfa_config.save()
        
        # Generate backup codes (TEMPORARY FIX - use 8-character codes)
        import random
        import string
        
        def generate_short_backup_codes(count=10):
            """Generate 8-character backup codes to fit in varchar(10)"""
            codes = []
            for _ in range(count):
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                codes.append(code)
            return codes
        
        backup_codes_list = generate_short_backup_codes(10)
        for backup_code in backup_codes_list:
            BackupCode.objects.create(user=user, code=backup_code)
        
        # Log the action
        MFALog.objects.create(
            user=user,
            action='enable',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            "message": "MFA enabled successfully",
            "backup_codes": backup_codes_list,
            "warning": "Save these backup codes in a secure place. They won't be shown again."
        }, status=status.HTTP_200_OK)
        
    except Token.DoesNotExist:
        return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
    except MFAConfiguration.DoesNotExist:
        return Response({"error": "MFA not configured for user"},
                       status=status.HTTP_400_BAD_REQUEST)

# ============================================================
# AUTHENTICATED MFA ENDPOINTS (for logged-in users)
# ============================================================

@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication]) 
@permission_classes([IsAuthenticated])
def mfa_setup_init(request):
    """Initialize MFA setup - generate secret and QR code (for logged-in users)"""
    user = request.user
    
    # Check if MFA is already enabled
    try:
        mfa_config = MFAConfiguration.objects.get(user=user)
        if mfa_config.is_enabled:
            return Response({
                "error": "MFA is already enabled for this account"
            }, status=status.HTTP_400_BAD_REQUEST)
        secret_key = mfa_config.secret_key
    except MFAConfiguration.DoesNotExist:
        # Generate new secret key
        secret_key = generate_secret_key()
        MFAConfiguration.objects.create(user=user, secret_key=secret_key, is_enabled=False)
    
    # Generate QR code
    qr_code_data = generate_qr_code(secret_key, user.email)
    
    return Response({
        "secret_key": secret_key,
        "qr_code": qr_code_data,
        "message": "Scan QR code with authenticator app"
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def mfa_enable(request):
    """Enable MFA after verifying code (for logged-in users)"""
    user = request.user
    code = request.data.get('code')
    
    if not code:
        return Response({"error": "Verification code is required"}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # Check rate limit
    if not check_rate_limit(user.id, 'mfa_enable', limit=3, window=300):
        return Response({"error": "Too many attempts. Please try again later."},
                       status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    try:
        mfa_config = MFAConfiguration.objects.get(user=user)
        
        # Verify the code
        if not verify_totp_code(mfa_config.secret_key, code):
            return Response({"error": "Invalid verification code"}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Enable MFA
        mfa_config.is_enabled = True
        mfa_config.save()
        
        # Generate backup codes
        backup_codes_list = generate_backup_codes(10)
        backup_codes = []
        for backup_code in backup_codes_list:
            bc = BackupCode.objects.create(
                user=user,
                code=backup_code
            )
            backup_codes.append(backup_code)
        
        # Log the action
        MFALog.objects.create(
            user=user,
            action='enable',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            "message": "MFA enabled successfully",
            "backup_codes": backup_codes,
            "warning": "Save these backup codes in a secure place. They won't be shown again."
        }, status=status.HTTP_200_OK)
        
    except MFAConfiguration.DoesNotExist:
        return Response({"error": "MFA not configured. Run setup first."},
                       status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def mfa_verify(request):
    """Verify MFA code for login"""
    code = request.data.get('code')
    user_id = request.data.get('user_id')
    
    if not all([code, user_id]):
        return Response({"error": "Code and user ID are required"},
                       status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(id=user_id)
        mfa_config = MFAConfiguration.objects.get(user=user, is_enabled=True)
        
        # Check rate limit
        if not check_rate_limit(user.id, 'mfa_verify', limit=5, window=300):
            return Response({"error": "Too many attempts. Please try again later."},
                           status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Try TOTP code first
        if verify_totp_code(mfa_config.secret_key, code):
            MFALog.objects.create(
                user=user,
                action='verify_success',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return Response({
                "verified": True,
                "message": "MFA verification successful"
            }, status=status.HTTP_200_OK)
        
        # Check backup codes
        try:
            backup_code = BackupCode.objects.get(
                user=user,
                code=code,
                is_used=False
            )
            backup_code.is_used = True
            backup_code.save()
            
            MFALog.objects.create(
                user=user,
                action='verify_success_backup',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                "verified": True,
                "message": "Backup code accepted",
                "warning": "This backup code has been used. Generate new ones if needed."
            }, status=status.HTTP_200_OK)
            
        except BackupCode.DoesNotExist:
            pass
        
        # Log failed attempt
        MFALog.objects.create(
            user=user,
            action='verify_failed',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            "verified": False,
            "error": "Invalid verification code"
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except (User.DoesNotExist, MFAConfiguration.DoesNotExist):
        return Response({"error": "MFA not enabled for this user"},
                       status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def mfa_disable(request):
    """Disable MFA for user"""
    user = request.user
    code = request.data.get('code')  # Require current MFA code to disable
    
    try:
        mfa_config = MFAConfiguration.objects.get(user=user, is_enabled=True)
        
        # Verify code before disabling
        if not verify_totp_code(mfa_config.secret_key, code):
            return Response({"error": "Invalid verification code"},
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Delete backup codes
        BackupCode.objects.filter(user=user).delete()
        
        # Disable MFA
        mfa_config.is_enabled = False
        mfa_config.save()
        
        # Log the action
        MFALog.objects.create(
            user=user,
            action='disable',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            "message": "MFA disabled successfully"
        }, status=status.HTTP_200_OK)
        
    except MFAConfiguration.DoesNotExist:
        return Response({"error": "MFA is not enabled"},
                       status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def mfa_status(request):
    """Get MFA status for current user"""
    user = request.user
    
    try:
        mfa_config = MFAConfiguration.objects.get(user=user)
        backup_codes = BackupCode.objects.filter(user=user, is_used=False)
        
        return Response({
            "is_enabled": mfa_config.is_enabled,
            "created_at": mfa_config.created_at,
            "backup_codes_count": backup_codes.count()
        }, status=status.HTTP_200_OK)
        
    except MFAConfiguration.DoesNotExist:
        return Response({
            "is_enabled": False,
            "message": "MFA not configured"
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def regenerate_backup_codes(request):
    """Regenerate backup codes"""
    user = request.user
    code = request.data.get('code')  # Require current MFA code
    
    try:
        mfa_config = MFAConfiguration.objects.get(user=user, is_enabled=True)
        
        # Verify code
        if not verify_totp_code(mfa_config.secret_key, code):
            return Response({"error": "Invalid verification code"},
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Delete old backup codes
        BackupCode.objects.filter(user=user).delete()
        
        # Generate new backup codes
        backup_codes_list = generate_backup_codes(10)
        backup_codes = []
        for backup_code in backup_codes_list:
            bc = BackupCode.objects.create(
                user=user,
                code=backup_code
            )
            backup_codes.append(backup_code)
        
        return Response({
            "message": "Backup codes regenerated",
            "backup_codes": backup_codes,
            "warning": "Save these new backup codes. Old codes are no longer valid."
        }, status=status.HTTP_200_OK)
        
    except MFAConfiguration.DoesNotExist:
        return Response({"error": "MFA is not enabled"},
                       status=status.HTTP_400_BAD_REQUEST)


# AWS Platform Info
@api_view(["GET"])
def aws_platform_info(request):
    """
    Returns platform AWS info needed to create IAM role
    """
    return Response({
        "platform_account_id": settings.PLATFORM_AWS_ACCOUNT_ID,
        "role_name": settings.AWS_ROLE_NAME,
    })


# In views.py - update AWS_POLICY
AWS_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                # Cost Explorer permissions
                "ce:GetCostAndUsage",
                "ce:GetCostForecast",
                "ce:GetDimensionValues",
                "ce:GetReservationUtilization",
                "ce:GetReservationCoverage",
                
                # Organizations permissions
                "organizations:ListAccounts",
                "organizations:DescribeAccount",
                
                # EC2 permissions
                "ec2:DescribeInstances",
                "ec2:DescribeRegions",
                "ec2:DescribeVpcs",
                "ec2:DescribeSubnets",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeVolumes",
                "ec2:DescribeTags",
                
                # S3 permissions
                "s3:ListAllMyBuckets",
                "s3:GetBucketLocation",
                "s3:GetBucketTagging",
                
                # RDS permissions
                "rds:DescribeDBInstances",
                "rds:DescribeDBSnapshots",
                "rds:ListTagsForResource",
                
                # Lambda permissions
                "lambda:ListFunctions",
                "lambda:GetFunction",
                "lambda:ListTags",
                
                # ELB/ALB permissions
                "elasticloadbalancing:DescribeLoadBalancers",
                "elasticloadbalancing:DescribeTags",
                
                # CloudFront permissions
                "cloudfront:ListDistributions",
                
                # ElastiCache permissions
                "elasticache:DescribeCacheClusters",
                "elasticache:ListTagsForResource",
                
                # DynamoDB permissions
                "dynamodb:ListTables",
                "dynamodb:DescribeTable",
                "dynamodb:ListTagsOfResource",
                
                # EKS permissions
                "eks:ListClusters",
                "eks:DescribeCluster",
                
                # API Gateway permissions
                "apigateway:GET",
                "apigateway:GetRestApis",
                "apigateway:GetStages",
                
                # SQS permissions
                "sqs:ListQueues",
                "sqs:ListQueueTags",
                
                # SNS permissions
                "sns:ListTopics",
                "sns:ListTagsForResource",
                
                # ECR permissions
                "ecr:DescribeRepositories",
                "ecr:ListTagsForResource",
                
                # CloudWatch permissions
                "cloudwatch:GetMetricData",
                "cloudwatch:ListMetrics",
                "cloudwatch:GetMetricStatistics",
                
                # IAM permissions
                "iam:ListUsers",
                "iam:ListRoles",
                "iam:ListPolicies",
                "iam:GetAccountSummary",
                
                # Additional permissions for other services
                "elasticbeanstalk:DescribeEnvironments",
                "elasticbeanstalk:DescribeApplications",
                "redshift:DescribeClusters",
                "opensearch:ListDomainNames",
                "opensearch:DescribeDomain",
                "efs:DescribeFileSystems",
                "route53:ListHostedZones",
                "kinesis:ListStreams"
            ],
            "Resource": "*"
        }
    ]
}

# 🔹 STEP B2
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_external_id(request):
    external_id = uuid.uuid4()

    # Store temporarily (no role ARN yet)
    AWSAccountConnection.objects.create(
        user=request.user,
        aws_account_id=settings.PLATFORM_AWS_ACCOUNT_ID,
        external_id=external_id,
        role_arn=""
    )

    return Response({
        "external_id": external_id,
        "aws_account_id": settings.PLATFORM_AWS_ACCOUNT_ID,
        "role_name": settings.AWS_ROLE_NAME,
        "policy_json": json.dumps(AWS_POLICY, indent=2),
    })

# 🔹 STEP B6 + C
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def connect_aws_account(request):
    role_arn = request.data.get("role_arn")

    if not role_arn:
        return Response({"error": "Role ARN required"}, status=400)

    record = AWSAccountConnection.objects.filter(
        user=request.user,
        role_arn=""
    ).last()

    if not record:
        return Response({"error": "External ID not found"}, status=400)

    # 🔁 STS AssumeRole
    sts = boto3.client("sts")
    try:
        sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName="cloudcost-session",
            ExternalId=str(record.external_id),
        )
    except Exception as e:
        return Response({"error": str(e)}, status=400)

    record.role_arn = role_arn
    record.save()

    return Response({
        "status": "connected",
        "message": "AWS account connected successfully"
    })


class AWSAccountViewSet(viewsets.ModelViewSet):
    queryset = AWSAccountConnection.objects.all()
    serializer_class = AWSAccountConnectionSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    
    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get all analytics data for frontend dashboard - with caching"""
        try:
            account = self.get_object()
            today = timezone.now().date()
            
            # Try cache first
            use_cache = request.GET.get('no_cache') != 'true'
            if use_cache:
                cached_analytics = ResourceCache.get_cached_cost_analytics(account.id)
                if cached_analytics:
                    print(f"📦 Serving cached analytics for account {account.id}")
                    serializer = CostAnalyticsSerializer(data=cached_analytics)
                    serializer.is_valid(raise_exception=True)
                    return Response(serializer.data)
            
            print(f"🔍 Fetching fresh analytics for account {account.aws_account_id}")
            
            # TRY TO GET REAL-TIME DATA FROM AWS API
            try:
                # Get AWS client
                ce_client = assume_role(account.role_arn, str(account.external_id))
                
                print(f"🔍 Fetching REAL-TIME data from AWS for account {account.aws_account_id}")
                
                # 1. Get CURRENT MONTH spend from AWS (REAL-TIME)
                current_month_total = Decimal(str(fetch_monthly_cost(ce_client)))
                print(f"   - Current month from AWS: ${current_month_total}")
                
                # 2. Get DAILY COSTS from AWS (last 90 days)
                aws_daily_costs = fetch_daily_costs(ce_client, days=90)
                print(f"   - Fetched {len(aws_daily_costs)} days of data from AWS")
                
                # 3. Calculate TOTAL HISTORICAL from AWS daily data
                total_historical_amount = Decimal('0')
                for day_cost in aws_daily_costs:
                    total_historical_amount += Decimal(str(day_cost['amount']))
                print(f"   - Total historical from AWS: ${total_historical_amount}")
                
                # 4. Get YESTERDAY'S spend from AWS (since today might not have data yet)
                yesterday = today - timedelta(days=1)
                yesterday_str = yesterday.strftime('%Y-%m-%d')
                yesterday_spend = Decimal('0')
                for day_cost in aws_daily_costs:
                    if day_cost['date'] == yesterday_str:
                        yesterday_spend = Decimal(str(day_cost['amount']))
                        break
                print(f"   - Yesterday's spend from AWS: ${yesterday_spend}")
                
                # 5. Get LAST 7 DAYS from AWS
                last_7_days = []
                for i in range(6, -1, -1):
                    target_date = today - timedelta(days=i)
                    target_date_str = target_date.strftime('%Y-%m-%d')
                    
                    amount = Decimal('0')
                    for day_cost in aws_daily_costs:
                        if day_cost['date'] == target_date_str:
                            amount = Decimal(str(day_cost['amount']))
                            break
                    
                    last_7_days.append({
                        'date': target_date.strftime('%a'),
                        'amount': amount,
                        'full_date': target_date_str,
                        'day_name': target_date.strftime('%A')
                    })
                
                # 6. Get month name
                month_name = today.strftime('%B')
                
                # 7. Calculate MONTHLY CHANGE
                monthly_change = Decimal('0')
                
                # Try to calculate from AWS daily data
                current_month_start = today.replace(day=1)
                current_month_aws_total = Decimal('0')
                last_month_aws_total = Decimal('0')
                
                # Calculate current month from AWS data
                for day_cost in aws_daily_costs:
                    day_date = datetime.strptime(day_cost['date'], '%Y-%m-%d').date()
                    amount = Decimal(str(day_cost['amount']))
                    
                    if day_date >= current_month_start:
                        current_month_aws_total += amount
                    elif day_date >= (current_month_start - timedelta(days=31)).replace(day=1):
                        last_month_aws_total += amount
                
                if last_month_aws_total > 0:
                    monthly_change = ((current_month_aws_total - last_month_aws_total) / last_month_aws_total) * 100
                    monthly_change = Decimal(str(round(float(monthly_change), 2)))
                
                # 8. Get FORECAST from database (or calculate simple one)
                monthly_summary = MonthlyCostSummary.objects.filter(account=account).first()
                if monthly_summary:
                    forecast_data = {
                        'thirtyDay': monthly_summary.forecast_30d or Decimal('0'),
                        'sevenDay': monthly_summary.forecast_7d or Decimal('0')
                    }
                else:
                    # Simple forecast based on current month average
                    days_passed = (today - current_month_start).days + 1
                    if days_passed > 0:
                        daily_avg = current_month_total / days_passed
                        forecast_data = {
                            'thirtyDay': daily_avg * 30,
                            'sevenDay': daily_avg * 7
                        }
                    else:
                        forecast_data = {
                            'thirtyDay': Decimal('0'),
                            'sevenDay': Decimal('0')
                        }
                
                # 9. Get SERVICE BREAKDOWN
                service_breakdown = []
                try:
                    service_breakdown = fetch_service_breakdown(ce_client, current_month_start, today)
                except Exception as e:
                    print(f"Service breakdown error: {e}")        
                                
                # Use AWS REAL-TIME data
                analytics_data = {
                    'total_spend': total_historical_amount.quantize(Decimal('0.01')),  # Round to 2 decimals
                    'current_month_spend': current_month_total.quantize(Decimal('0.01')),  # Round to 2 decimals
                    'current_month_name': month_name,
                    'today_spend': yesterday_spend.quantize(Decimal('0.01')),  # Round to 2 decimals
                    'monthly_change': monthly_change.quantize(Decimal('0.1')),  # Round to 1 decimal
                    'forecast': forecast_data,
                    'daily_spend': last_7_days,
                    'service_breakdown': service_breakdown,
                    'cached': False,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Also round forecast values
                analytics_data['forecast']['thirtyDay'] = analytics_data['forecast']['thirtyDay'].quantize(Decimal('0.01')) if analytics_data['forecast']['thirtyDay'] else Decimal('0')
                analytics_data['forecast']['sevenDay'] = analytics_data['forecast']['sevenDay'].quantize(Decimal('0.01')) if analytics_data['forecast']['sevenDay'] else Decimal('0')
                
                # Round daily spend amounts for display
                for day in analytics_data['daily_spend']:
                    day['amount'] = day['amount'].quantize(Decimal('0.01'))
                
            except Exception as aws_error:
                print(f"❌ AWS API failed: {aws_error}")
                print("⚠️ Falling back to database data...")
                # Fallback to database if AWS API fails
                analytics_data = self._get_analytics_from_database(account, today)
            
            # Cache the results
            ResourceCache.cache_cost_analytics(account.id, analytics_data)
            
            serializer = CostAnalyticsSerializer(data=analytics_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data)
            
        except Exception as e:
            print(f"❌ Error in analytics view: {str(e)}")
            return Response({'error': str(e)}, status=500)
        
    def _get_analytics_from_database(self, account, today):
        """Fallback: Get analytics from database if AWS API fails"""
        # 1. TOTAL HISTORICAL SPEND
        total_historical_spends = DailySpend.objects.filter(account=account)
        total_historical_amount = Decimal('0')
        for spend in total_historical_spends:
            total_historical_amount += spend.amount

        # 2. CURRENT MONTH SPEND
        current_month_start = today.replace(day=1)
        current_month_spends = DailySpend.objects.filter(
            account=account,
            date__gte=current_month_start
        )
        current_month_total = Decimal('0')
        for spend in current_month_spends:
            current_month_total += spend.amount

        # 3. YESTERDAY'S SPEND
        yesterday = today - timedelta(days=1)
        yesterday_spend_obj = DailySpend.objects.filter(
            account=account,
            date=yesterday
        ).first()
        yesterday_spend = yesterday_spend_obj.amount if yesterday_spend_obj else Decimal('0')

        # 4. LAST 7 DAYS
        last_7_days = []
        for i in range(6, -1, -1):
            target_date = today - timedelta(days=i)
            spend = DailySpend.objects.filter(
                account=account,
                date=target_date
            ).first()
            amount = spend.amount if spend else Decimal('0')
            last_7_days.append({
                'date': target_date.strftime('%a'),
                'amount': amount,
                'full_date': target_date.strftime('%Y-%m-%d'),
                'day_name': target_date.strftime('%A')
            })

        # 5. MONTHLY CHANGE
        monthly_change = Decimal('0')
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        last_month_spends = DailySpend.objects.filter(
            account=account,
            date__gte=last_month_start,
            date__lt=current_month_start
        )

        if last_month_spends.exists():
            last_month_total = sum([spend.amount for spend in last_month_spends])
            if last_month_total > 0 and current_month_total > 0:
                try:
                    monthly_change = ((current_month_total - Decimal(str(last_month_total))) / Decimal(str(last_month_total))) * 100
                    monthly_change = Decimal(str(round(float(monthly_change), 2)))
                except (ZeroDivisionError, OverflowError):
                    monthly_change = Decimal('0')

        # 6. FORECAST
        monthly_summary = MonthlyCostSummary.objects.filter(account=account).first()
        forecast_data = {
            'thirtyDay': monthly_summary.forecast_30d if monthly_summary else Decimal('0'),
            'sevenDay': monthly_summary.forecast_7d if monthly_summary else Decimal('0')
        }

        # ROUND all values for display
        return {
            'total_spend': total_historical_amount.quantize(Decimal('0.01')),
            'current_month_spend': current_month_total.quantize(Decimal('0.01')),
            'current_month_name': today.strftime('%B'),
            'today_spend': yesterday_spend.quantize(Decimal('0.01')),
            'monthly_change': monthly_change.quantize(Decimal('0.1')),
            'forecast': {
                'thirtyDay': forecast_data['thirtyDay'].quantize(Decimal('0.01')) if forecast_data['thirtyDay'] else Decimal('0'),
                'sevenDay': forecast_data['sevenDay'].quantize(Decimal('0.01')) if forecast_data['sevenDay'] else Decimal('0')
            },
            'daily_spend': last_7_days,
        }    

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Manually trigger cost sync - FETCHES REAL AWS DATA"""
        try:
            account = self.get_object()
            
            print(f"🔄 Starting MANUAL SYNC for AWS account: {account.aws_account_id}")
            
            # Import tasks
            from .tasks import (
                fetch_aws_costs,
                update_monthly_summary,
                update_cost_forecast,
                update_recent_daily_spend
            )
            
            # IMPORTANT: Clear old data first to ensure fresh sync
            from .models import DailySpend, MonthlyCostSummary, RecentDailySpend
            print("🧹 Clearing old data to ensure fresh sync...")
            
            # Clear data for this account only
            DailySpend.objects.filter(account=account).delete()
            MonthlyCostSummary.objects.filter(account=account).delete()
            RecentDailySpend.objects.filter(account=account).delete()
            
            print("✅ Old data cleared")
            
            # Run tasks sequentially with progress tracking
            print("1️⃣ Fetching AWS costs from Cost Explorer API...")
            if not fetch_aws_costs(str(account.id)):
                return Response({
                    'status': 'error',
                    'message': 'Failed to fetch AWS costs. Check AWS credentials and permissions.'
                }, status=500)
            print("✅ AWS costs fetched")
            
            print("2️⃣ Updating monthly summary...")
            if not update_monthly_summary(str(account.id)):
                return Response({
                    'status': 'warning',
                    'message': 'Monthly summary updated but some calculations may be incomplete'
                })
            print("✅ Monthly summary updated")
            
            print("3️⃣ Updating cost forecasts...")
            if not update_cost_forecast(str(account.id)):
                return Response({
                    'status': 'warning',
                    'message': 'Cost forecasts updated but may be based on limited data'
                })
            print("✅ Cost forecasts updated")
            
            print("4️⃣ Updating recent daily spends...")
            if not update_recent_daily_spend(str(account.id)):
                return Response({
                    'status': 'warning',
                    'message': 'Recent daily spends updated but may have incomplete data'
                })
            print("✅ Recent daily spends updated")
            
            # Update last sync time
            account.last_synced = timezone.now()
            account.save()
            
            # Get updated counts to show what was synced
            daily_count = DailySpend.objects.filter(account=account).count()
            recent_data = RecentDailySpend.objects.filter(account=account).first()
            
            return Response({
                'status': 'success',
                'message': 'Sync completed successfully with REAL AWS data',
                'last_sync': account.last_synced,
                'details': {
                    'daily_records_synced': daily_count,
                    'account_id': account.aws_account_id,
                    'has_recent_data': recent_data is not None
                }
            })
            
        except Exception as e:
            print(f"❌ Sync failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Sync failed: {str(e)}'
            }, status=500)

class FetchAWSCostsView(generics.GenericAPIView):
    """Fetch costs from AWS Cost Explorer"""
    permission_classes = [IsAuthenticated]
    
    def get_aws_client(self, account):
        """Get AWS client using STS AssumeRole - FIXED: Remove hardcoded credentials"""
        try:
            # Use environment variables for AWS credentials
            # The boto3 client will automatically use AWS credentials from:
            # 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
            # 2. AWS credentials file (~/.aws/credentials)
            # 3. IAM role (if running on EC2)
            
            # Use STS to assume role
            sts_client = boto3.client('sts', region_name='us-east-1')
            
            # Assume the role with external ID
            assumed_role = sts_client.assume_role(
                RoleArn=account.role_arn,
                RoleSessionName=f"CloudCostApp_{account.aws_account_id}",
                ExternalId=str(account.external_id)
            )
            
            # Create Cost Explorer client
            ce_client = boto3.client(
                'ce',
                aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
                aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
                aws_session_token=assumed_role['Credentials']['SessionToken'],
                region_name='us-east-1'
            )
            
            return ce_client
        except Exception as e:
            print(f"Error getting AWS client: {str(e)}")
            return None
    
    def post(self, request, account_id):
        try:
            account = AWSAccountConnection.objects.get(
                id=account_id, 
                user=request.user
            )
            
            # Get AWS client
            ce_client = self.get_aws_client(account)
            if not ce_client:
                return Response({'error': 'Failed to connect to AWS'}, status=400)
            
            # Calculate date ranges
            today = timezone.now().date()
            start_date = today - timedelta(days=90)  # Get last 90 days
            
            # Fetch cost data
            response = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': today.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost']
            )
            
            # Process and save daily costs
            results = response.get('ResultsByTime', [])
            for day_result in results:
                date_str = day_result['TimePeriod']['Start']
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                amount = Decimal(day_result['Total']['UnblendedCost']['Amount'])
                
                # Save daily spend
                DailySpend.objects.update_or_create(
                    account=account,
                    date=date_obj,
                    defaults={'amount': amount}
                )
            
            # Update last sync time
            account.last_synced = timezone.now()
            account.save()
            
            return Response({
                'status': 'success',
                'days_updated': len(results),
                'last_sync': account.last_synced
            })
            
        except AWSAccountConnection.DoesNotExist:
            return Response({'error': 'Account not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


# In views.py - add this for debugging
@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def check_auth(request):
    return JsonResponse({
        "authenticated": True,
        "username": request.user.username,
        "email": request.user.email,
        "aws_accounts": request.user.aws_accounts.count()
    })


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def debug_monthly_change(request, account_id):
    """Debug monthly change calculation"""
    try:
        account = AWSAccountConnection.objects.get(id=account_id, user=request.user)
        
        today = timezone.now().date()
        current_month_start = today.replace(day=1)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        
        # Get spends
        current_spends = DailySpend.objects.filter(
            account=account,
            date__gte=current_month_start
        )
        last_spends = DailySpend.objects.filter(
            account=account,
            date__gte=last_month_start,
            date__lt=current_month_start
        )
        
        current_total = sum([float(s.amount) for s in current_spends])
        last_total = sum([float(s.amount) for s in last_spends])
        
        monthly_change = 0
        if last_total > 0:
            monthly_change = ((current_total - last_total) / last_total) * 100
        
        return Response({
            'account_id': account_id,
            'current_month': {
                'start_date': current_month_start,
                'total': current_total,
                'days_count': current_spends.count(),
                'sample_amounts': [float(s.amount) for s in current_spends[:3]]
            },
            'last_month': {
                'start_date': last_month_start,
                'total': last_total,
                'days_count': last_spends.count(),
                'sample_amounts': [float(s.amount) for s in last_spends[:3]]
            },
            'monthly_change': {
                'raw': monthly_change,
                'formatted': f"{monthly_change:.2f}%",
                'digits_count': len(str(int(abs(monthly_change)))),
                'is_problematic': abs(monthly_change) > 9999.99
            },
            'issue': 'Serializer expects max_digits=10 but value might exceed this'
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)

from .cache_utils import ResourceCache
from django.core.cache import cache

# views.py - Update ResourceViewSet class

class ResourceViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    
    def get_account(self, pk, user):
        """Helper to get account with permission check"""
        return AWSAccountConnection.objects.get(id=pk, user=user)
    
    @action(detail=True, methods=['get'])
    def resources(self, request, pk=None):
        """Get AWS resources being used - with caching"""
        try:
            account = self.get_account(pk, request.user)
            
            # Try cache first
            use_cache = request.GET.get('no_cache') != 'true'
            if use_cache:
                cached_resources = ResourceCache.get_cached_resources(account.id)
                if cached_resources:
                    print(f"📦 Serving cached resources for account {account.id}")
                    return Response(cached_resources)
            
            # Fetch fresh resources
            resources = get_aws_resources(account.id, use_cache=use_cache)
            if not resources:
                return Response({
                    'error': 'Failed to fetch resources'
                }, status=500)
            
            return Response(resources)
        except AWSAccountConnection.DoesNotExist:
            return Response({'error': 'Account not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    @action(detail=True, methods=['get'], url_path='resource-summary')
    def resource_summary(self, request, pk=None):
        """Get summary of resource usage - with caching"""
        try:
            account = self.get_account(pk, request.user)
            
            # Try cache first
            use_cache = request.GET.get('no_cache') != 'true'
            if use_cache:
                cached_summary = ResourceCache.get_cached_resource_summary(account.id)
                if cached_summary:
                    print(f"📦 Serving cached resource summary for account {account.id}")
                    return Response(cached_summary)
            
            # Fetch fresh summary
            summary = get_resource_usage_summary(account.id, use_cache=use_cache)
            if not summary:
                # Try to get from database
                try:
                    db_summary = ResourceSummary.objects.get(account=account)
                    summary = db_summary.to_dict()
                    summary['cached'] = True
                    summary['source'] = 'database_fallback'
                except ResourceSummary.DoesNotExist:
                    return Response({
                        'error': 'No resource data available'
                    }, status=404)
            
            return Response(summary)
        except AWSAccountConnection.DoesNotExist:
            return Response({'error': 'Account not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    @action(detail=True, methods=['post'], url_path='clear-cache')
    def clear_cache(self, request, pk=None):
        """Clear cache for this account"""
        try:
            account = self.get_account(pk, request.user)
            ResourceCache.invalidate_account_cache(account.id)
            return Response({
                'status': 'success',
                'message': f'Cache cleared for account {account.aws_account_id}'
            })
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    @action(detail=True, methods=['get'], url_path='from-database')
    def resource_summary_db(self, request, pk=None):
        """Get resource summary directly from database"""
        try:
            account = self.get_account(pk, request.user)
            summary = ResourceSummary.objects.get(account=account)
            serializer = ResourceSummarySerializer(summary)
            return Response(serializer.data)
        except ResourceSummary.DoesNotExist:
            return Response({'error': 'No resource summary in database'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    @action(detail=True, methods=['get'], url_path='paid-resources')
    def paid_resources(self, request, pk=None):
        """Get all paid AWS resources categorized by cost impact"""
        try:
            account = AWSAccountConnection.objects.get(id=pk, user=request.user)
            
            # Try cache first
            use_cache = request.GET.get('no_cache') != 'true'
            if use_cache:
                cached_resources = ResourceCache.get_cached_resources(account.id)
                if cached_resources:
                    print(f"📦 Serving cached paid resources for account {account.id}")
                    return Response(cached_resources)
            
            # Fetch fresh resources
            resources = get_all_paid_resources(account.id, use_cache=use_cache)
            if not resources:
                return Response({
                    'error': 'Failed to fetch paid resources'
                }, status=500)
            
            return Response(resources)
        except AWSAccountConnection.DoesNotExist:
            return Response({'error': 'Account not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    @action(detail=True, methods=['get'], url_path='cost-analysis')
    def cost_analysis(self, request, pk=None):
        """Get cost analysis and recommendations"""
        try:
            account = AWSAccountConnection.objects.get(id=pk, user=request.user)
            
            analysis = analyze_cost_impact(account.id)
            if not analysis:
                return Response({
                    'error': 'Failed to analyze cost impact'
                }, status=500)
            
            return Response(analysis)
        except AWSAccountConnection.DoesNotExist:
            return Response({'error': 'Account not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)    


    
@action(detail=True, methods=['get'])
def resource_summary(self, request, pk=None):
            
            """Get summary of resource usage - with caching"""
            try:
                account = AWSAccountConnection.objects.get(id=pk, user=request.user)
                
                # Try cache first
                use_cache = request.GET.get('no_cache') != 'true'
                if use_cache:
                    cached_summary = ResourceCache.get_cached_resource_summary(account.id)
                    if cached_summary:
                        print(f"📦 Serving cached resource summary for account {account.id}")
                        return Response(cached_summary)
                
                # Fetch fresh summary
                summary = get_resource_usage_summary(account.id, use_cache=use_cache)
                if not summary:
                    return Response({
                        'error': 'Failed to fetch resource summary'
                    }, status=500)
                
                return Response(summary)
                
            except AWSAccountConnection.DoesNotExist:
                return Response({'error': 'Account not found'}, status=404)
            except Exception as e:
                return Response({'error': str(e)}, status=500)
        


@action(detail=True, methods=['post'])
def clear_cache(self, request, pk=None):
        """Clear cache for this account"""
        try:
            account = AWSAccountConnection.objects.get(id=pk, user=request.user)
            ResourceCache.invalidate_account_cache(account.id)
            return Response({
                'status': 'success',
                'message': f'Cache cleared for account {account.aws_account_id}'
            })
        except Exception as e:
            return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def test_resources(request, account_id):
    """Test endpoint for resource tracking"""
    try:
        account = AWSAccountConnection.objects.get(id=account_id, user=request.user)
        
        # Test getting resources
        print(f"Testing resource tracking for account: {account.aws_account_id}")
        
        resources = get_aws_resources(account.id)
        summary = get_resource_usage_summary(account.id)
        
        return Response({
            'account': account.aws_account_id,
            'has_resources': resources is not None,
            'has_summary': summary is not None,
            'summary': summary,
            'ec2_count': len(resources['ec2_instances']) if resources else 0,
            's3_count': len(resources['s3_buckets']) if resources else 0,
            'lambda_count': len(resources['lambda_functions']) if resources else 0,
            'rds_count': len(resources['rds_instances']) if resources else 0
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    



# In views.py - add this endpoint
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def check_permissions(request, account_id):
    """Check what permissions the role has"""
    try:
        account = AWSAccountConnection.objects.get(id=account_id, user=request.user)
        
        # Get AWS client
        ce_client = assume_role(account.role_arn, str(account.external_id))
        
        # Test various permissions
        permissions_status = {
            'cost_explorer': False,
            'ec2': False,
            's3': False,
            'rds': False,
            'lambda': False,
            'elb': False,
            'cloudfront': False,
            'elasticache': False,
            'dynamodb': False,
            'eks': False,
            'apigateway': False,
            'sqs': False,
            'sns': False
        }
        
        # Test Cost Explorer
        try:
            today = datetime.now().date()
            start = today.replace(day=1)
            ce_client.get_cost_and_usage(
                TimePeriod={
                    "Start": start.isoformat(),
                    "End": today.isoformat(),
                },
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
            )
            permissions_status['cost_explorer'] = True
        except:
            permissions_status['cost_explorer'] = False
        
        # Return the status
        return Response({
            'account_id': account.aws_account_id,
            'role_arn': account.role_arn,
            'permissions_status': permissions_status,
            'next_steps': 'Update IAM policy to include missing permissions'
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def low_level_services(request, account_id):
    """Get low-level AWS services with pricing information and store in DB"""
    try:
        account = AWSAccountConnection.objects.get(id=account_id, user=request.user)
        
        # Check if we should use cache or force refresh
        use_cache = request.GET.get('no_cache') != 'true'
        store_in_db = request.GET.get('store') != 'false'  # Default to True
        
        start_time = time.time()
        
        # Discover low-level services using Version 1
        services_data = discover_low_level_services(account_id, use_cache=use_cache)
        
        # Store in database if requested
        if store_in_db and 'error' not in services_data:
            try:
                store_low_level_services_snapshot(account, services_data)
            except Exception as db_error:
                print(f"Error storing in database: {db_error}")
                # Continue even if DB storage fails
        
        # Add scan duration
        services_data['scan_duration'] = time.time() - start_time
        
        return Response(services_data)
        
    except AWSAccountConnection.DoesNotExist:
        return Response({'error': 'Account not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

def store_low_level_services_snapshot(account, services_data):
    """Store low-level services data in database"""
    with transaction.atomic():
        
        # 1. Create snapshot record
        snapshot = LowLevelServiceSnapshot.objects.create(
            account=account,
            total_services=services_data['summary']['total_services'],
            estimated_monthly_cost=Decimal(str(services_data['summary']['estimated_monthly_cost'])),
            unique_service_types=services_data['summary']['unique_service_types'],
            unique_services_discovered=services_data['summary'].get('unique_services_discovered', 0),
            regions_scanned=services_data['summary'].get('regions_scanned', []),
            snapshot_data=services_data,
            scan_duration_seconds=services_data.get('scan_duration')
        )
        
        # 2. Deactivate old resources
        LowLevelServiceResource.objects.filter(
            account=account, 
            is_active=True
        ).update(is_active=False)
        
        # 3. Store/update service definitions and resources
        for service_id, service_data in services_data['services_by_category'].items():
            
            # Get or create category
            category, _ = LowLevelServiceCategory.objects.get_or_create(
                key=service_data['category'].lower().replace(' ', '_'),
                defaults={'name': service_data['category']}
            )
            
            # Get or create service definition
            service_def, _ = LowLevelServiceDefinition.objects.get_or_create(
                service_id=service_id,
                defaults={
                    'name': service_data['service_info']['name'],
                    'description': service_data['service_info']['description'],
                    'category': category,
                    'unit': service_data['service_info'].get('unit', ''),
                    
                    # Map all pricing fields
                    'price_per_hour': Decimal(str(service_data['service_info'].get('price_per_hour', 0))) if service_data['service_info'].get('price_per_hour') else None,
                    'price_per_gb': Decimal(str(service_data['service_info'].get('price_per_gb', 0))) if service_data['service_info'].get('price_per_gb') else None,
                    'price_per_gb_month': Decimal(str(service_data['service_info'].get('price_per_gb_month', 0))) if service_data['service_info'].get('price_per_gb_month') else None,
                    'price_per_gb_second': Decimal(str(service_data['service_info'].get('price_per_gb_second', 0))) if service_data['service_info'].get('price_per_gb_second') else None,
                    'price_per_million': Decimal(str(service_data['service_info'].get('price_per_million', 0))) if service_data['service_info'].get('price_per_million') else None,
                    'price_per_10k': Decimal(str(service_data['service_info'].get('price_per_10k', 0))) if service_data['service_info'].get('price_per_10k') else None,
                    'price_per_vcpu_hour': Decimal(str(service_data['service_info'].get('price_per_vcpu_hour', 0))) if service_data['service_info'].get('price_per_vcpu_hour') else None,
                    'price_per_iops_hour': Decimal(str(service_data['service_info'].get('price_per_iops_hour', 0))) if service_data['service_info'].get('price_per_iops_hour') else None,
                    'price_per_month': Decimal(str(service_data['service_info'].get('price_per_month', 0))) if service_data['service_info'].get('price_per_month') else None,
                }
            )
            
            # Create or update resources
            for resource in service_data['resources']:
                LowLevelServiceResource.objects.update_or_create(
                    account=account,
                    service_definition=service_def,
                    resource_id=resource['resource_id'],
                    region=resource['region'],
                    defaults={
                        'resource_name': resource['resource_name'],
                        'count': resource['count'],
                        'estimated_monthly_cost': Decimal(str(resource['estimated_monthly_cost'])),
                        'details': resource.get('details', {}),
                        'discovered_at': snapshot.created_at,
                        'is_active': True
                    }
                )
            
            # 4. Update cost history (daily aggregation)
            today = timezone.now().date()
            total_cost = Decimal(str(service_data['total_monthly_cost']))
            resource_count = service_data['total_count']
            
            LowLevelServiceCostHistory.objects.update_or_create(
                account=account,
                service_definition=service_def,
                date=today,
                defaults={
                    'monthly_cost': total_cost,
                    'resource_count': resource_count,
                    'region_breakdown': {
                        resource['region']: Decimal(str(resource['estimated_monthly_cost']))
                        for resource in service_data['resources']
                    }
                }
            )
        
        return snapshot  


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def low_level_services_by_category(request, account_id, category):
    """Get low-level services filtered by category (e.g., 'compute', 'storage', 'ml')"""
    try:
        account = AWSAccountConnection.objects.get(id=account_id, user=request.user)
        
        services_data = discover_low_level_services(
            account_id, 
            use_cache=request.GET.get('no_cache') != 'true'
        )
        
        # Filter by category if specified
        if category and 'services_by_category' in services_data:
            filtered_services = {
                k: v for k, v in services_data['services_by_category'].items()
                if v.get('category', '').lower() == category.lower()
            }
            services_data['services_by_category'] = filtered_services
            
        return Response(services_data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def low_level_cost_summary(request, account_id):
    """Get simplified cost summary for low-level services"""
    try:
        account = AWSAccountConnection.objects.get(id=account_id, user=request.user)
        
        services_data = discover_low_level_services(
            account_id, 
            use_cache=request.GET.get('no_cache') != 'true'
        )
        
        summary = services_data.get('summary', {})
        
        # Enhanced summary for Version 1's rich data
        response_data = {
            'total_monthly_cost': summary.get('estimated_monthly_cost', 0),
            'total_resources': summary.get('total_services', 0),
            'unique_service_types': summary.get('unique_service_types', 0),
            'unique_services': summary.get('unique_services_discovered', 0),
            'regions': summary.get('regions_scanned', []),
            'last_updated': summary.get('timestamp'),
            'cost_by_category': {}
        }
        
        # Calculate cost by category
        for service_id, service_data in services_data.get('services_by_category', {}).items():
            category = service_data.get('category', 'Other')
            cost = service_data.get('total_monthly_cost', 0)
            
            if category not in response_data['cost_by_category']:
                response_data['cost_by_category'][category] = 0
            response_data['cost_by_category'][category] += cost
        
        return Response(response_data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def export_low_level_services(request, account_id, format='json'):
    """Export low-level services data in JSON or CSV format"""
    try:
        account = AWSAccountConnection.objects.get(id=account_id, user=request.user)
        
        services_data = discover_low_level_services(
            account_id, 
            use_cache=request.GET.get('no_cache') != 'true'
        )
        
        if format == 'csv':
            # Flatten the resources for CSV export
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            
            # Write headers
            writer.writerow(['Service', 'Resource ID', 'Resource Name', 'Region', 
                           'Monthly Cost', 'Category', 'Details'])
            
            # Write rows
            for resource in services_data.get('all_resources', []):
                writer.writerow([
                    resource.get('service_id', ''),
                    resource.get('resource_id', ''),
                    resource.get('resource_name', ''),
                    resource.get('region', ''),
                    resource.get('estimated_monthly_cost', 0),
                    services_data.get('services_by_category', {})
                        .get(resource.get('service_id'), {})
                        .get('category', ''),
                    str(resource.get('details', {}))
                ])
            
            response = Response(output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="low_level_services_{account_id}.csv"'
            return response
        else:
            return Response(services_data)
            
    except Exception as e:
        return Response({'error': str(e)}, status=500)