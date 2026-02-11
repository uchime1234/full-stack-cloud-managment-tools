# resource_tracker.py
import boto3
from datetime import datetime, timedelta, timezone
from django.utils import timezone as django_timezone
from .models import AWSAccountConnection
from .models import ResourceSummary  # Import the new model
from botocore.exceptions import ClientError
from .cache_utils import ResourceCache

# ============================================================
# COST CATEGORIES FOR AWS RESOURCES
# ============================================================

COST_CATEGORIES = {
    # COMPUTE (Most expensive category)
    'ec2': {
        'name': 'EC2 Instances',
        'description': 'Elastic Compute Cloud - Virtual servers',
        'cost_driver': 'Instance type, running hours, data transfer',
        'cost_level': 'HIGH',
        'services': ['ec2']
    },
    'lambda': {
        'name': 'Lambda Functions',
        'description': 'Serverless compute service',
        'cost_driver': 'Execution time, memory, requests',
        'cost_level': 'MEDIUM',
        'services': ['lambda']
    },
    'eks': {
        'name': 'EKS Clusters',
        'description': 'Managed Kubernetes Service',
        'cost_driver': 'Worker nodes, control plane ($0.10/hour)',
        'cost_level': 'HIGH',
        'services': ['eks']
    },
    'elastic_beanstalk': {
        'name': 'Elastic Beanstalk',
        'description': 'Platform as a Service',
        'cost_driver': 'Underlying resources (EC2, RDS, etc.)',
        'cost_level': 'MEDIUM',
        'services': ['elastic_beanstalk']
    },
    
    # DATABASE (Often high cost)
    'rds': {
        'name': 'RDS Databases',
        'description': 'Relational Database Service',
        'cost_driver': 'Instance type, storage, IOPS, multi-AZ',
        'cost_level': 'HIGH',
        'services': ['rds']
    },
    'dynamodb': {
        'name': 'DynamoDB',
        'description': 'NoSQL Database',
        'cost_driver': 'Read/write capacity units, storage',
        'cost_level': 'MEDIUM',
        'services': ['dynamodb']
    },
    'elasticache': {
        'name': 'ElastiCache',
        'description': 'Managed Redis/Memcached',
        'cost_driver': 'Node type, data transfer',
        'cost_level': 'MEDIUM',
        'services': ['elasticache']
    },
    'redshift': {
        'name': 'Redshift',
        'description': 'Data Warehouse',
        'cost_driver': 'Node type, storage, data processed',
        'cost_level': 'HIGH',
        'services': ['redshift']
    },
    
    # STORAGE (Variable cost)
    's3': {
        'name': 'S3 Storage',
        'description': 'Object Storage',
        'cost_driver': 'Storage class, requests, data transfer',
        'cost_level': 'MEDIUM',
        'services': ['s3']
    },
    'efs': {
        'name': 'EFS',
        'description': 'Elastic File System',
        'cost_driver': 'Storage used, throughput',
        'cost_level': 'MEDIUM',
        'services': ['efs']
    },
    'ebs': {
        'name': 'EBS Volumes',
        'description': 'Block storage for EC2',
        'cost_driver': 'Volume type, size, IOPS',
        'cost_level': 'MEDIUM',
        'services': ['ebs']
    },
    
    # NETWORKING & CONTENT DELIVERY
    'cloudfront': {
        'name': 'CloudFront',
        'description': 'Content Delivery Network',
        'cost_driver': 'Data transfer out, requests',
        'cost_level': 'MEDIUM',
        'services': ['cloudfront']
    },
    'load_balancers': {
        'name': 'Load Balancers',
        'description': 'Application/Network Load Balancers',
        'cost_driver': 'LCU hours, data processed',
        'cost_level': 'MEDIUM',
        'services': ['elbv2', 'elb']
    },
    'api_gateway': {
        'name': 'API Gateway',
        'description': 'Managed API service',
        'cost_driver': 'API calls, data transfer',
        'cost_level': 'MEDIUM',
        'services': ['apigateway']
    },
    'nat_gateway': {
        'name': 'NAT Gateway',
        'description': 'Network Address Translation',
        'cost_driver': 'Gateway hours, data processed',
        'cost_level': 'MEDIUM',
        'services': ['ec2']  # NAT Gateway is part of EC2 service
    },
    
    # ANALYTICS & BIG DATA
    'kinesis': {
        'name': 'Kinesis',
        'description': 'Real-time data streaming',
        'cost_driver': 'Shard hours, PUT payload units',
        'cost_level': 'MEDIUM',
        'services': ['kinesis']
    },
    
    # MACHINE LEARNING & AI
    'comprehend': {
        'name': 'Comprehend',
        'description': 'NLP Service',
        'cost_driver': 'Characters processed',
        'cost_level': 'MEDIUM',
        'services': ['comprehend']
    },
    
    # MANAGEMENT & GOVERNANCE
    'cloudwatch': {
        'name': 'CloudWatch',
        'description': 'Monitoring & Observability',
        'cost_driver': 'Metrics, logs, alarms, dashboards',
        'cost_level': 'MEDIUM',
        'services': ['cloudwatch']
    },
    'config': {
        'name': 'Config',
        'description': 'Configuration & Compliance',
        'cost_driver': 'Configuration items, rules evaluated',
        'cost_level': 'MEDIUM',
        'services': ['config']
    },
    
    # SECURITY, IDENTITY & COMPLIANCE
    'secrets_manager': {
        'name': 'Secrets Manager',
        'description': 'Secrets Management',
        'cost_driver': 'Secrets stored, API calls',
        'cost_level': 'LOW',
        'services': ['secretsmanager']
    },
    
    # APPLICATION INTEGRATION
    'sqs': {
        'name': 'SQS',
        'description': 'Simple Queue Service',
        'cost_driver': 'Requests, data transfer',
        'cost_level': 'LOW',
        'services': ['sqs']
    },
    'sns': {
        'name': 'SNS',
        'description': 'Simple Notification Service',
        'cost_driver': 'Notifications, data transfer',
        'cost_level': 'LOW',
        'services': ['sns']
    },
    
    # CONTAINERS
    'ecr': {
        'name': 'ECR',
        'description': 'Elastic Container Registry',
        'cost_driver': 'Storage, data transfer',
        'cost_level': 'LOW',
        'services': ['ecr']
    },
    
    # DEVELOPER TOOLS
    'codebuild': {
        'name': 'CodeBuild',
        'description': 'Build Service',
        'cost_driver': 'Compute minutes',
        'cost_level': 'MEDIUM',
        'services': ['codebuild']
    },
    
    # END USER COMPUTING
    'workspaces': {
        'name': 'WorkSpaces',
        'description': 'Virtual Desktops',
        'cost_driver': 'Running hours, storage, bundles',
        'cost_level': 'HIGH',
        'services': ['workspaces']
    }
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def assume_role_for_account(account):
    """Assume role for AWS account using platform credentials"""
    try:
        # Use platform credentials from environment
        sts = boto3.client('sts')
        creds = sts.assume_role(
            RoleArn=account.role_arn,
            RoleSessionName="ResourceTracker",
            ExternalId=str(account.external_id)
        )["Credentials"]
        return creds
    except Exception as e:
        print(f"Error assuming role: {e}")
        return None

def get_aws_client(service_name, creds, region='us-east-1'):
    """Create AWS client with assumed role credentials"""
    try:
        return boto3.client(
            service_name,
            aws_access_key_id=creds['AccessKeyId'],
            aws_secret_access_key=creds['SecretAccessKey'],
            aws_session_token=creds['SessionToken'],
            region_name=region
        )
    except Exception as e:
        print(f"Error creating {service_name} client: {e}")
        return None

def calculate_running_hours(launch_time):
    """Calculate how many hours an instance has been running"""
    if not launch_time:
        return 0
    
    try:
        if isinstance(launch_time, str):
            if launch_time.endswith('Z'):
                launch_time = launch_time[:-1] + '+00:00'
            launch_time = datetime.fromisoformat(launch_time)
        
        if launch_time.tzinfo is None:
            launch_time = launch_time.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        running_time = now - launch_time
        return round(running_time.total_seconds() / 3600, 1)
        
    except Exception as e:
        print(f"Error calculating running hours: {e}")
        return 0

def calculate_age_days(creation_date):
    """Calculate age in days"""
    if not creation_date:
        return 0
    
    try:
        if isinstance(creation_date, str):
            if creation_date.endswith('Z'):
                creation_date = creation_date[:-1] + '+00:00'
            creation_date = datetime.fromisoformat(creation_date)
        
        if creation_date.tzinfo is None:
            creation_date = creation_date.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        age = now - creation_date
        return age.days
        
    except Exception as e:
        print(f"Error calculating age days: {e}")
        return 0

# ============================================================
# PAID RESOURCES TRACKING FUNCTIONS
# ============================================================

def get_all_paid_resources(account_id, use_cache=True):
    """Get all AWS resources that can incur charges, categorized by cost impact"""
    try:
        # Try cache first
        if use_cache:
            cached_resources = ResourceCache.get_cached_resources(account_id)
            if cached_resources and 'cost_categories' in cached_resources:
                print(f"📦 Using cached paid resources for account {account_id}")
                return cached_resources
        
        account = AWSAccountConnection.objects.get(id=account_id)
        creds = assume_role_for_account(account)
        
        if not creds:
            return None
        
        # Initialize resources structure with cost categories
        resources = {
            'cost_categories': {},
            'summary': {
                'total_paid_resources': 0,
                'high_cost_resources': 0,
                'medium_cost_resources': 0,
                'low_cost_resources': 0,
                'categories_found': 0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            'raw_resources': {},
            'permissions_issues': []
        }
        
        # Initialize all cost categories
        for category_key, category_info in COST_CATEGORIES.items():
            resources['cost_categories'][category_key] = {
                'name': category_info['name'],
                'description': category_info['description'],
                'cost_level': category_info['cost_level'],
                'cost_driver': category_info['cost_driver'],
                'resources': [],
                'count': 0,
                'estimated_monthly_cost': 0
            }
        
        # EC2 Instances (Most common cost driver)
        try:
            ec2 = get_aws_client('ec2', creds)
            if ec2:
                ec2_response = ec2.describe_instances()
                for reservation in ec2_response.get('Reservations', []):
                    for instance in reservation.get('Instances', []):
                        instance_info = {
                            'id': instance.get('InstanceId'),
                            'type': instance.get('InstanceType'),
                            'state': instance.get('State', {}).get('Name'),
                            'launch_time': instance.get('LaunchTime'),
                            'running_hours': calculate_running_hours(instance.get('LaunchTime')),
                            'tags': {tag['Key']: tag['Value'] for tag in instance.get('Tags', []) if 'Key' in tag and 'Value' in tag}
                        }
                        resources['cost_categories']['ec2']['resources'].append(instance_info)
                        resources['cost_categories']['ec2']['count'] += 1
                        
                        # Also add to raw_resources for backward compatibility
                        if 'ec2_instances' not in resources['raw_resources']:
                            resources['raw_resources']['ec2_instances'] = []
                        resources['raw_resources']['ec2_instances'].append(instance_info)
        except Exception as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown') if hasattr(e, 'response') else 'Unknown'
            if error_code == 'AccessDenied':
                resources['permissions_issues'].append('EC2: Access denied')
                print(f"⚠️ EC2 Access Denied: Missing ec2:DescribeInstances permission")
            else:
                print(f"EC2 Error: {e}")
        
        # S3 Buckets
        try:
            s3 = get_aws_client('s3', creds)
            if s3:
                s3_response = s3.list_buckets()
                for bucket in s3_response.get('Buckets', []):
                    bucket_info = {
                        'name': bucket.get('Name'),
                        'creation_date': bucket.get('CreationDate'),
                        'age_days': calculate_age_days(bucket.get('CreationDate'))
                    }
                    resources['cost_categories']['s3']['resources'].append(bucket_info)
                    resources['cost_categories']['s3']['count'] += 1
                    
                    # Also add to raw_resources
                    if 's3_buckets' not in resources['raw_resources']:
                        resources['raw_resources']['s3_buckets'] = []
                    resources['raw_resources']['s3_buckets'].append(bucket_info)
        except Exception as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown') if hasattr(e, 'response') else 'Unknown'
            if error_code == 'AccessDenied':
                resources['permissions_issues'].append('S3: Access denied')
                print(f"⚠️ S3 Access Denied: Missing s3:ListAllMyBuckets permission")
            else:
                print(f"S3 Error: {e}")
        
        # Lambda Functions
        try:
            lambda_client = get_aws_client('lambda', creds)
            if lambda_client:
                lambda_response = lambda_client.list_functions()
                for function in lambda_response.get('Functions', []):
                    function_info = {
                        'name': function.get('FunctionName'),
                        'runtime': function.get('Runtime'),
                        'memory_size': function.get('MemorySize'),
                        'timeout': function.get('Timeout'),
                        'last_modified': function.get('LastModified'),
                        'code_size': function.get('CodeSize')
                    }
                    resources['cost_categories']['lambda']['resources'].append(function_info)
                    resources['cost_categories']['lambda']['count'] += 1
                    
                    # Also add to raw_resources
                    if 'lambda_functions' not in resources['raw_resources']:
                        resources['raw_resources']['lambda_functions'] = []
                    resources['raw_resources']['lambda_functions'].append(function_info)
        except Exception as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown') if hasattr(e, 'response') else 'Unknown'
            if error_code == 'AccessDenied':
                resources['permissions_issues'].append('Lambda: Access denied')
                print(f"⚠️ Lambda Access Denied: Missing lambda:ListFunctions permission")
            else:
                print(f"Lambda Error: {e}")
        
        # RDS Instances
        try:
            rds = get_aws_client('rds', creds)
            if rds:
                rds_response = rds.describe_db_instances()
                for db_instance in rds_response.get('DBInstances', []):
                    db_info = {
                        'id': db_instance.get('DBInstanceIdentifier'),
                        'engine': db_instance.get('Engine'),
                        'instance_class': db_instance.get('DBInstanceClass'),
                        'status': db_instance.get('DBInstanceStatus'),
                        'allocated_storage': db_instance.get('AllocatedStorage'),
                        'multi_az': db_instance.get('MultiAZ', False),
                        'created_time': db_instance.get('InstanceCreateTime')
                    }
                    resources['cost_categories']['rds']['resources'].append(db_info)
                    resources['cost_categories']['rds']['count'] += 1
                    
                    # Also add to raw_resources
                    if 'rds_instances' not in resources['raw_resources']:
                        resources['raw_resources']['rds_instances'] = []
                    resources['raw_resources']['rds_instances'].append(db_info)
        except Exception as e:
            print(f"RDS Error: {e}")
        
        # DynamoDB Tables
        try:
            dynamodb = get_aws_client('dynamodb', creds)
            if dynamodb:
                ddb_response = dynamodb.list_tables()
                for table_name in ddb_response.get('TableNames', []):
                    try:
                        table_info = dynamodb.describe_table(TableName=table_name)['Table']
                        ddb_info = {
                            'name': table_name,
                            'status': table_info.get('TableStatus'),
                            'creation_date': table_info.get('CreationDateTime'),
                            'item_count': table_info.get('ItemCount', 0),
                            'billing_mode': table_info.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED')
                        }
                        resources['cost_categories']['dynamodb']['resources'].append(ddb_info)
                        resources['cost_categories']['dynamodb']['count'] += 1
                        
                        # Also add to raw_resources
                        if 'dynamodb_tables' not in resources['raw_resources']:
                            resources['raw_resources']['dynamodb_tables'] = []
                        resources['raw_resources']['dynamodb_tables'].append(ddb_info)
                    except Exception as e:
                        print(f"DynamoDB table {table_name} error: {e}")
        except Exception as e:
            print(f"DynamoDB Error: {e}")
        
        # ElastiCache Clusters
        try:
            elasticache = get_aws_client('elasticache', creds)
            if elasticache:
                ec_response = elasticache.describe_cache_clusters()
                for cluster in ec_response.get('CacheClusters', []):
                    ec_info = {
                        'id': cluster.get('CacheClusterId'),
                        'engine': cluster.get('Engine'),
                        'status': cluster.get('CacheClusterStatus'),
                        'node_type': cluster.get('CacheNodeType'),
                        'num_nodes': cluster.get('NumCacheNodes', 0)
                    }
                    resources['cost_categories']['elasticache']['resources'].append(ec_info)
                    resources['cost_categories']['elasticache']['count'] += 1
                    
                    # Also add to raw_resources
                    if 'elasticache_clusters' not in resources['raw_resources']:
                        resources['raw_resources']['elasticache_clusters'] = []
                    resources['raw_resources']['elasticache_clusters'].append(ec_info)
        except Exception as e:
            print(f"ElastiCache Error: {e}")
        
        # EKS Clusters
        try:
            eks = get_aws_client('eks', creds)
            if eks:
                eks_response = eks.list_clusters()
                for cluster_name in eks_response.get('clusters', []):
                    try:
                        cluster_info_resp = eks.describe_cluster(name=cluster_name)
                        cluster_info = cluster_info_resp.get('cluster', {})
                        eks_info = {
                            'name': cluster_name,
                            'status': cluster_info.get('status'),
                            'version': cluster_info.get('version'),
                            'created_at': cluster_info.get('createdAt')
                        }
                        resources['cost_categories']['eks']['resources'].append(eks_info)
                        resources['cost_categories']['eks']['count'] += 1
                        
                        # Also add to raw_resources
                        if 'eks_clusters' not in resources['raw_resources']:
                            resources['raw_resources']['eks_clusters'] = []
                        resources['raw_resources']['eks_clusters'].append(eks_info)
                    except Exception as e:
                        print(f"EKS cluster {cluster_name} error: {e}")
        except Exception as e:
            print(f"EKS Error: {e}")
        
        # CloudFront Distributions
        try:
            cloudfront = get_aws_client('cloudfront', creds)
            if cloudfront:
                cf_response = cloudfront.list_distributions()
                if cf_response.get('DistributionList', {}).get('Items'):
                    for dist in cf_response['DistributionList']['Items']:
                        cf_info = {
                            'id': dist.get('Id'),
                            'domain_name': dist.get('DomainName'),
                            'status': dist.get('Status'),
                            'enabled': dist.get('Enabled', False),
                            'price_class': dist.get('PriceClass', 'PriceClass_All')
                        }
                        resources['cost_categories']['cloudfront']['resources'].append(cf_info)
                        resources['cost_categories']['cloudfront']['count'] += 1
                        
                        # Also add to raw_resources
                        if 'cloudfront_distributions' not in resources['raw_resources']:
                            resources['raw_resources']['cloudfront_distributions'] = []
                        resources['raw_resources']['cloudfront_distributions'].append(cf_info)
        except Exception as e:
            print(f"CloudFront Error: {e}")
        
        # Load Balancers
        try:
            elbv2 = get_aws_client('elbv2', creds)
            if elbv2:
                elb_response = elbv2.describe_load_balancers()
                for lb in elb_response.get('LoadBalancers', []):
                    lb_info = {
                        'arn': lb.get('LoadBalancerArn'),
                        'name': lb.get('LoadBalancerName'),
                        'type': lb.get('Type'),
                        'scheme': lb.get('Scheme'),
                        'state': lb.get('State', {}).get('Code'),
                        'created_time': lb.get('CreatedTime')
                    }
                    resources['cost_categories']['load_balancers']['resources'].append(lb_info)
                    resources['cost_categories']['load_balancers']['count'] += 1
                    
                    # Also add to raw_resources
                    if 'load_balancers' not in resources['raw_resources']:
                        resources['raw_resources']['load_balancers'] = []
                    resources['raw_resources']['load_balancers'].append(lb_info)
        except Exception as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown') if hasattr(e, 'response') else 'Unknown'
            if error_code == 'AccessDenied':
                resources['permissions_issues'].append('ELB: Access denied')
                print(f"⚠️ ELB Access Denied: Missing elasticloadbalancing:DescribeLoadBalancers permission")
            else:
                print(f"ELB Error: {e}")
        
        # API Gateway
        try:
            apigateway = get_aws_client('apigateway', creds)
            if apigateway:
                api_response = apigateway.get_rest_apis()
                for api in api_response.get('items', []):
                    api_info = {
                        'id': api.get('id'),
                        'name': api.get('name'),
                        'created_date': api.get('createdDate'),
                        'description': api.get('description', '')
                    }
                    resources['cost_categories']['api_gateway']['resources'].append(api_info)
                    resources['cost_categories']['api_gateway']['count'] += 1
                    
                    # Also add to raw_resources
                    if 'api_gateway_apis' not in resources['raw_resources']:
                        resources['raw_resources']['api_gateway_apis'] = []
                    resources['raw_resources']['api_gateway_apis'].append(api_info)
        except Exception as e:
            print(f"API Gateway Error: {e}")
        
        # SQS Queues
        try:
            sqs = get_aws_client('sqs', creds)
            if sqs:
                sqs_response = sqs.list_queues()
                if sqs_response.get('QueueUrls'):
                    for queue_url in sqs_response['QueueUrls']:
                        queue_name = queue_url.split('/')[-1]
                        sqs_info = {
                            'name': queue_name,
                            'url': queue_url
                        }
                        resources['cost_categories']['sqs']['resources'].append(sqs_info)
                        resources['cost_categories']['sqs']['count'] += 1
                        
                        # Also add to raw_resources
                        if 'sqs_queues' not in resources['raw_resources']:
                            resources['raw_resources']['sqs_queues'] = []
                        resources['raw_resources']['sqs_queues'].append(sqs_info)
        except Exception as e:
            print(f"SQS Error: {e}")
        
        # SNS Topics
        try:
            sns = get_aws_client('sns', creds)
            if sns:
                sns_response = sns.list_topics()
                for topic in sns_response.get('Topics', []):
                    topic_arn = topic.get('TopicArn', '')
                    topic_name = topic_arn.split(':')[-1]
                    sns_info = {
                        'name': topic_name,
                        'arn': topic_arn
                    }
                    resources['cost_categories']['sns']['resources'].append(sns_info)
                    resources['cost_categories']['sns']['count'] += 1
                    
                    # Also add to raw_resources
                    if 'sns_topics' not in resources['raw_resources']:
                        resources['raw_resources']['sns_topics'] = []
                    resources['raw_resources']['sns_topics'].append(sns_info)
        except Exception as e:
            print(f"SNS Error: {e}")
        
        # ECR Repositories
        try:
            ecr = get_aws_client('ecr', creds)
            if ecr:
                ecr_response = ecr.describe_repositories()
                for repo in ecr_response.get('repositories', []):
                    ecr_info = {
                        'name': repo.get('repositoryName'),
                        'arn': repo.get('repositoryArn'),
                        'created_at': repo.get('createdAt'),
                        'image_tag_mutability': repo.get('imageTagMutability')
                    }
                    resources['cost_categories']['ecr']['resources'].append(ecr_info)
                    resources['cost_categories']['ecr']['count'] += 1
                    
                    # Also add to raw_resources
                    if 'ecr_repositories' not in resources['raw_resources']:
                        resources['raw_resources']['ecr_repositories'] = []
                    resources['raw_resources']['ecr_repositories'].append(ecr_info)
        except Exception as e:
            print(f"ECR Error: {e}")
        
        # Redshift Clusters
        try:
            redshift = get_aws_client('redshift', creds)
            if redshift:
                redshift_response = redshift.describe_clusters()
                for cluster in redshift_response.get('Clusters', []):
                    redshift_info = {
                        'id': cluster.get('ClusterIdentifier'),
                        'node_type': cluster.get('NodeType'),
                        'status': cluster.get('ClusterStatus'),
                        'created_time': cluster.get('ClusterCreateTime'),
                        'number_of_nodes': cluster.get('NumberOfNodes', 0)
                    }
                    resources['cost_categories']['redshift']['resources'].append(redshift_info)
                    resources['cost_categories']['redshift']['count'] += 1
                    
                    # Also add to raw_resources
                    if 'redshift_clusters' not in resources['raw_resources']:
                        resources['raw_resources']['redshift_clusters'] = []
                    resources['raw_resources']['redshift_clusters'].append(redshift_info)
        except Exception as e:
            print(f"Redshift Error: {e}")
        
        # EFS File Systems
        try:
            efs = get_aws_client('efs', creds)
            if efs:
                efs_response = efs.describe_file_systems()
                for fs in efs_response.get('FileSystems', []):
                    efs_info = {
                        'id': fs.get('FileSystemId'),
                        'creation_time': fs.get('CreationTime'),
                        'lifecycle_state': fs.get('LifeCycleState'),
                        'size_bytes': fs.get('SizeInBytes', {}).get('Value', 0)
                    }
                    resources['cost_categories']['efs']['resources'].append(efs_info)
                    resources['cost_categories']['efs']['count'] += 1
                    
                    # Also add to raw_resources
                    if 'efs_file_systems' not in resources['raw_resources']:
                        resources['raw_resources']['efs_file_systems'] = []
                    resources['raw_resources']['efs_file_systems'].append(efs_info)
        except Exception as e:
            print(f"EFS Error: {e}")
        
        # EBS Volumes (important cost driver)
        try:
            ec2 = get_aws_client('ec2', creds)
            if ec2:
                ebs_response = ec2.describe_volumes()
                for volume in ebs_response.get('Volumes', []):
                    ebs_info = {
                        'id': volume.get('VolumeId'),
                        'size_gb': volume.get('Size'),
                        'type': volume.get('VolumeType'),
                        'state': volume.get('State'),
                        'iops': volume.get('Iops'),
                        'throughput': volume.get('Throughput'),
                        'created_time': volume.get('CreateTime')
                    }
                    resources['cost_categories']['ebs']['resources'].append(ebs_info)
                    resources['cost_categories']['ebs']['count'] += 1
        except Exception as e:
            print(f"EBS Error: {e}")
        
        # Update summary statistics
        total_paid_resources = 0
        high_cost_resources = 0
        medium_cost_resources = 0
        low_cost_resources = 0
        categories_found = 0
        
        for category_key in resources['cost_categories']:
            count = resources['cost_categories'][category_key]['count']
            if count > 0:
                total_paid_resources += count
                categories_found += 1
                
                cost_level = resources['cost_categories'][category_key]['cost_level']
                if cost_level == 'HIGH':
                    high_cost_resources += count
                elif cost_level == 'MEDIUM':
                    medium_cost_resources += count
                elif cost_level == 'LOW':
                    low_cost_resources += count
        
        resources['summary'].update({
            'total_paid_resources': total_paid_resources,
            'high_cost_resources': high_cost_resources,
            'medium_cost_resources': medium_cost_resources,
            'low_cost_resources': low_cost_resources,
            'categories_found': categories_found
        })
        
        # Cache the results
        ResourceCache.cache_resources(account_id, resources)
        
        return resources
        
    except AWSAccountConnection.DoesNotExist:
        print(f"Account {account_id} not found")
        return None
    except Exception as e:
        print(f"Error getting paid resources: {e}")
        return None

def analyze_cost_impact(account_id):
    """Analyze potential cost impact of resources"""
    resources = get_all_paid_resources(account_id)
    
    if not resources or 'cost_categories' not in resources:
        return None
    
    analysis = {
        'high_risk_findings': [],
        'medium_risk_findings': [],
        'low_risk_findings': [],
        'recommendations': [],
        'estimated_savings_potential': 0,
        'summary': {
            'total_resources': resources['summary']['total_paid_resources'],
            'high_cost_categories': 0,
            'medium_cost_categories': 0,
            'low_cost_categories': 0
        }
    }
    
    # Check for stopped EC2 instances
    if 'ec2' in resources['cost_categories'] and resources['cost_categories']['ec2']['count'] > 0:
        stopped_instances = [inst for inst in resources['cost_categories']['ec2']['resources'] 
                           if inst.get('state') == 'stopped']
        if stopped_instances:
            analysis['high_risk_findings'].append({
                'category': 'EC2',
                'issue': f'Found {len(stopped_instances)} stopped EC2 instances',
                'impact': 'You are paying for EBS storage but not using compute',
                'recommendation': 'Terminate or start these instances',
                'potential_savings': f'${len(stopped_instances) * 20:.2f}/month (estimate)'
            })
    
    # Check for idle RDS instances
    if 'rds' in resources['cost_categories'] and resources['cost_categories']['rds']['count'] > 0:
        analysis['medium_risk_findings'].append({
            'category': 'RDS',
            'issue': f'Found {resources["cost_categories"]["rds"]["count"]} RDS instances',
            'impact': 'RDS can be expensive, especially with Multi-AZ and Provisioned IOPS',
            'recommendation': 'Review instance sizing and consider Aurora Serverless for variable workloads',
            'potential_savings': 'Varies by instance type'
        })
    
    # Check for old S3 buckets
    if 's3' in resources['cost_categories'] and resources['cost_categories']['s3']['count'] > 0:
        old_buckets = [bucket for bucket in resources['cost_categories']['s3']['resources'] 
                      if bucket.get('age_days', 0) > 365]
        if old_buckets:
            analysis['low_risk_findings'].append({
                'category': 'S3',
                'issue': f'Found {len(old_buckets)} S3 buckets older than 1 year',
                'impact': 'May contain unused data incurring storage costs',
                'recommendation': 'Review bucket contents and lifecycle policies',
                'potential_savings': 'Depends on storage size'
            })
    
    # Check for idle load balancers
    if 'load_balancers' in resources['cost_categories'] and resources['cost_categories']['load_balancers']['count'] > 0:
        analysis['medium_risk_findings'].append({
            'category': 'Load Balancers',
            'issue': f'Found {resources["cost_categories"]["load_balancers"]["count"]} load balancers',
            'impact': 'Load balancers incur hourly charges even when idle',
            'recommendation': 'Delete unused load balancers',
            'potential_savings': f'${resources["cost_categories"]["load_balancers"]["count"] * 18:.2f}/month (estimate)'
        })
    
    # Check for unencrypted EBS volumes
    if 'ebs' in resources['cost_categories'] and resources['cost_categories']['ebs']['count'] > 0:
        analysis['medium_risk_findings'].append({
            'category': 'EBS',
            'issue': f'Found {resources["cost_categories"]["ebs"]["count"]} EBS volumes',
            'impact': 'EBS storage costs can add up quickly',
            'recommendation': 'Review volume sizes and consider snapshots for unused volumes',
            'potential_savings': 'Varies by volume size and type'
        })
    
    # Calculate summary
    for category_key, category in resources['cost_categories'].items():
        if category['count'] > 0:
            if category['cost_level'] == 'HIGH':
                analysis['summary']['high_cost_categories'] += 1
            elif category['cost_level'] == 'MEDIUM':
                analysis['summary']['medium_cost_categories'] += 1
            elif category['cost_level'] == 'LOW':
                analysis['summary']['low_cost_categories'] += 1
    
    # Generate overall recommendations
    if analysis['high_risk_findings']:
        analysis['recommendations'].append('Address high-risk findings first to maximize savings')
    if analysis['medium_risk_findings']:
        analysis['recommendations'].append('Review medium-risk resources for optimization opportunities')
    if resources['summary']['total_paid_resources'] > 50:
        analysis['recommendations'].append('Consider using AWS Cost Explorer for detailed cost analysis')
    
    return analysis

# ============================================================
# ORIGINAL FUNCTIONS (for backward compatibility)
# ============================================================

def get_all_aws_resources(account_id, use_cache=True):
    """Get ALL AWS resources being used - with caching support (for backward compatibility)"""
    paid_resources = get_all_paid_resources(account_id, use_cache)
    
    if not paid_resources:
        return None
    
    # Convert to old format for backward compatibility
    resources = {
        'ec2_instances': paid_resources.get('raw_resources', {}).get('ec2_instances', []),
        'rds_instances': paid_resources.get('raw_resources', {}).get('rds_instances', []),
        's3_buckets': paid_resources.get('raw_resources', {}).get('s3_buckets', []),
        'lambda_functions': paid_resources.get('raw_resources', {}).get('lambda_functions', []),
        'load_balancers': paid_resources.get('raw_resources', {}).get('load_balancers', []),
        'cloudfront_distributions': paid_resources.get('raw_resources', {}).get('cloudfront_distributions', []),
        'elasticache_clusters': paid_resources.get('raw_resources', {}).get('elasticache_clusters', []),
        'redshift_clusters': paid_resources.get('raw_resources', {}).get('redshift_clusters', []),
        'eks_clusters': paid_resources.get('raw_resources', {}).get('eks_clusters', []),
        'elastic_beanstalk_apps': [],
        'api_gateway_apis': paid_resources.get('raw_resources', {}).get('api_gateway_apis', []),
        'dynamodb_tables': paid_resources.get('raw_resources', {}).get('dynamodb_tables', []),
        'efs_file_systems': paid_resources.get('raw_resources', {}).get('efs_file_systems', []),
        'opensearch_domains': [],
        'sqs_queues': paid_resources.get('raw_resources', {}).get('sqs_queues', []),
        'sns_topics': paid_resources.get('raw_resources', {}).get('sns_topics', []),
        'ecr_repositories': paid_resources.get('raw_resources', {}).get('ecr_repositories', []),
        'summary': {
            'total_instances': len(paid_resources.get('raw_resources', {}).get('ec2_instances', [])),
            'running_instances': len([inst for inst in paid_resources.get('raw_resources', {}).get('ec2_instances', []) 
                                     if inst.get('state') == 'running']),
            'total_buckets': len(paid_resources.get('raw_resources', {}).get('s3_buckets', [])),
            'total_functions': len(paid_resources.get('raw_resources', {}).get('lambda_functions', [])),
            'total_resources': sum(len(res_list) for res_list in paid_resources.get('raw_resources', {}).values())
        },
        'permissions_issues': paid_resources.get('permissions_issues', [])
    }
    
    return resources

# Alias for backward compatibility
get_aws_resources = get_all_aws_resources

# ============================================================
# RESOURCE SUMMARY FUNCTIONS
# ============================================================

def get_resource_usage_summary(account_id, use_cache=True):
    """Get summary of resource usage - with caching and database storage"""
    try:
        # Try cache first
        if use_cache:
            cached_summary = ResourceCache.get_cached_resource_summary(account_id)
            if cached_summary:
                return cached_summary
        
        account = AWSAccountConnection.objects.get(id=account_id)
        resources = get_all_paid_resources(account_id, use_cache=False)
        
        if not resources:
            # Try to get from database if available
            try:
                db_summary = ResourceSummary.objects.get(account=account)
                summary_dict = db_summary.to_dict()
                summary_dict['cached'] = True
                summary_dict['source'] = 'database'
                # Cache it
                ResourceCache.cache_resource_summary(account_id, summary_dict)
                return summary_dict
            except ResourceSummary.DoesNotExist:
                return None
        
        # Calculate summary from resources
        summary = {
            'total_resources': resources['summary']['total_paid_resources'],
            'ec2': {
                'total': resources['cost_categories'].get('ec2', {}).get('count', 0),
                'running': len([inst for inst in resources['cost_categories'].get('ec2', {}).get('resources', []) 
                               if inst.get('state') == 'running']),
                'stopped': len([inst for inst in resources['cost_categories'].get('ec2', {}).get('resources', []) 
                               if inst.get('state') == 'stopped'])
            },
            's3': {
                'total_buckets': resources['cost_categories'].get('s3', {}).get('count', 0)
            },
            'lambda': {
                'total_functions': resources['cost_categories'].get('lambda', {}).get('count', 0)
            },
            'rds': {
                'total_instances': resources['cost_categories'].get('rds', {}).get('count', 0)
            },
            'load_balancers': {
                'total': resources['cost_categories'].get('load_balancers', {}).get('count', 0)
            },
            'cloudfront': {
                'total': resources['cost_categories'].get('cloudfront', {}).get('count', 0)
            },
            'elasticache': {
                'total': resources['cost_categories'].get('elasticache', {}).get('count', 0)
            },
            'eks': {
                'total': resources['cost_categories'].get('eks', {}).get('count', 0)
            },
            'api_gateway': {
                'total': resources['cost_categories'].get('api_gateway', {}).get('count', 0)
            },
            'dynamodb': {
                'total': resources['cost_categories'].get('dynamodb', {}).get('count', 0)
            },
            'sqs': {
                'total': resources['cost_categories'].get('sqs', {}).get('count', 0)
            },
            'sns': {
                'total': resources['cost_categories'].get('sns', {}).get('count', 0)
            },
            'permissions_issues': resources.get('permissions_issues', []),
            'cost_analysis': analyze_cost_impact(account_id)
        }
        
        # Calculate average running hours for EC2
        ec2_resources = resources['cost_categories'].get('ec2', {}).get('resources', [])
        if ec2_resources:
            total_hours = sum(inst.get('running_hours', 0) for inst in ec2_resources)
            summary['ec2']['avg_running_hours'] = round(total_hours / len(ec2_resources), 1)
        else:
            summary['ec2']['avg_running_hours'] = 0
        
        # Calculate average age for S3 buckets
        s3_resources = resources['cost_categories'].get('s3', {}).get('resources', [])
        if s3_resources:
            total_age = sum(bucket.get('age_days', 0) for bucket in s3_resources)
            summary['s3']['avg_age_days'] = round(total_age / len(s3_resources), 1)
        else:
            summary['s3']['avg_age_days'] = 0
        
        # SAVE TO DATABASE
        save_resource_summary_to_db(account, summary)
        
        # Cache the summary
        summary['cached'] = False
        summary['source'] = 'aws_api'
        ResourceCache.cache_resource_summary(account_id, summary)
        
        return summary
    except Exception as e:
        print(f"Error getting resource summary: {e}")
        return None

def save_resource_summary_to_db(account, summary_data):
    """Save resource summary to database"""
    try:
        ResourceSummary.objects.update_or_create(
            account=account,
            defaults={
                'total_resources': summary_data.get('total_resources', 0),
                'ec2_total': summary_data.get('ec2', {}).get('total', 0),
                'ec2_running': summary_data.get('ec2', {}).get('running', 0),
                'ec2_stopped': summary_data.get('ec2', {}).get('stopped', 0),
                'ec2_avg_running_hours': summary_data.get('ec2', {}).get('avg_running_hours', 0),
                's3_total_buckets': summary_data.get('s3', {}).get('total_buckets', 0),
                's3_avg_age_days': summary_data.get('s3', {}).get('avg_age_days', 0),
                'lambda_total_functions': summary_data.get('lambda', {}).get('total_functions', 0),
                'rds_total_instances': summary_data.get('rds', {}).get('total_instances', 0),
                'load_balancers_total': summary_data.get('load_balancers', {}).get('total', 0),
                'cloudfront_total': summary_data.get('cloudfront', {}).get('total', 0),
                'elasticache_total': summary_data.get('elasticache', {}).get('total', 0),
                'eks_total': summary_data.get('eks', {}).get('total', 0),
                'api_gateway_total': summary_data.get('api_gateway', {}).get('total', 0),
                'dynamodb_total': summary_data.get('dynamodb', {}).get('total', 0),
                'sqs_total': summary_data.get('sqs', {}).get('total', 0),
                'sns_total': summary_data.get('sns', {}).get('total', 0),
                'permissions_issues': summary_data.get('permissions_issues', [])
            }
        )
        print(f"✅ Saved resource summary to database for {account.aws_account_id}")
    except Exception as e:
        print(f"❌ Error saving resource summary to database: {e}")