# low_level_tracker.py
import boto3
from datetime import datetime
from django.utils import timezone
from botocore.exceptions import ClientError
from .models import AWSAccountConnection
from .cache_utils import ResourceCache
import concurrent.futures
import threading

# ============================================================
# COMPLETE LOW-LEVEL SERVICE CATEGORIES & PRICING
# ============================================================
# EVERY AWS SERVICE WITH ALL LOW-LEVEL COMPONENTS
# ============================================================

LOW_LEVEL_SERVICES = {
    # ========== NETWORKING & CONTENT DELIVERY ==========
    'vpc': {
        'name': 'Virtual Private Cloud',
        'low_level_services': [
            {
                'id': 'internet_gateway',
                'name': 'Internet Gateway',
                'description': 'VPC internet connectivity',
                'price_per_hour': 0.00,
                'price_per_gb': None,
                'unit': 'per gateway'
            },
            {
                'id': 'nat_gateway',
                'name': 'NAT Gateway',
                'description': 'Outbound internet for private subnets',
                'price_per_hour': 0.045,
                'price_per_gb': 0.045,
                'unit': 'per gateway + data processed'
            },
            {
                'id': 'vpc_endpoint',
                'name': 'VPC Endpoints',
                'description': 'Private AWS service access',
                'price_per_hour': 0.01,
                'price_per_gb': 0.01,
                'unit': 'per endpoint-hour + data processed'
            },
            {
                'id': 'vpc_peering',
                'name': 'VPC Peering',
                'description': 'Cross-VPC connectivity',
                'price_per_hour': 0.00,
                'price_per_gb': 0.01,
                'unit': 'per GB transferred'
            },
            {
                'id': 'transit_gateway',
                'name': 'Transit Gateway',
                'description': 'Hub-and-spoke networking',
                'price_per_hour': 0.05,
                'price_per_gb': 0.02,
                'unit': 'per gateway-hour + data processed'
            },
            {
                'id': 'transit_gateway_attachment',
                'name': 'Transit Gateway Attachment',
                'description': 'Network attachments to Transit Gateway',
                'price_per_hour': 0.05,
                'unit': 'per attachment-hour'
            },
            {
                'id': 'vpn_connection',
                'name': 'VPN Connections',
                'description': 'Site-to-site VPN',
                'price_per_hour': 0.05,
                'price_per_gb': 0.09,
                'unit': 'per connection-hour + data processed'
            },
            {
                'id': 'client_vpn_endpoint',
                'name': 'Client VPN Endpoint',
                'description': 'OpenVPN-based remote access',
                'price_per_hour': 0.10,
                'price_per_gb': 0.05,
                'unit': 'per endpoint-hour + data processed'
            },
            {
                'id': 'network_acl',
                'name': 'Network ACL',
                'description': 'Stateless firewall rules',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'security_group',
                'name': 'Security Group',
                'description': 'Stateful firewall rules',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'subnet',
                'name': 'Subnet',
                'description': 'Network segmentation',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'route_table',
                'name': 'Route Table',
                'description': 'Network traffic routing',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'elastic_ip',
                'name': 'Elastic IP Address',
                'description': 'Static public IPv4',
                'price_per_hour': 0.005,
                'unit': 'per address-hour (unattached)'
            },
            {
                'id': 'eni',
                'name': 'Elastic Network Interface',
                'description': 'Virtual network card',
                'price_per_hour': 0.00,
                'unit': 'free (standard)'
            },
            {
                'id': 'eni_enhanced',
                'name': 'Enhanced ENI',
                'description': 'Enhanced networking interface',
                'price_per_hour': 0.012,
                'unit': 'per interface-hour'
            },
            {
                'id': 'flow_logs',
                'name': 'VPC Flow Logs',
                'description': 'IP traffic logs',
                'price_per_gb': 0.50,
                'unit': 'per GB ingested'
            },
            {
                'id': 'prefix_list',
                'name': 'Prefix List',
                'description': 'CIDR block management',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'network_performance_metrics',
                'name': 'Network Performance Metrics',
                'description': 'VPC monitoring metrics',
                'price_per_hour': 0.00,
                'unit': 'free (CloudWatch metrics billed)'
            }
        ]
    },
    
    'direct_connect': {
        'name': 'AWS Direct Connect',
        'low_level_services': [
            {
                'id': 'dx_connection_1gbps',
                'name': 'Direct Connect 1Gbps',
                'description': 'Physical dedicated connection',
                'price_per_hour': 0.30,
                'unit': 'per port-hour'
            },
            {
                'id': 'dx_connection_10gbps',
                'name': 'Direct Connect 10Gbps',
                'description': 'Physical dedicated connection',
                'price_per_hour': 2.25,
                'unit': 'per port-hour'
            },
            {
                'id': 'dx_virtual_interface_private',
                'name': 'Private Virtual Interface',
                'description': 'VPC connectivity',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'dx_virtual_interface_public',
                'name': 'Public Virtual Interface',
                'description': 'Public AWS services connectivity',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'dx_virtual_interface_transit',
                'name': 'Transit Virtual Interface',
                'description': 'Transit Gateway connectivity',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'dx_gateway',
                'name': 'Direct Connect Gateway',
                'description': 'Multi-VPC access',
                'price_per_hour': 0.10,
                'unit': 'per gateway-hour'
            },
            {
                'id': 'dx_macsec',
                'name': 'MACsec Encryption',
                'description': 'Link layer encryption',
                'price_per_hour': 0.075,
                'unit': 'per port-hour'
            }
        ]
    },
    
    'global_accelerator': {
        'name': 'AWS Global Accelerator',
        'low_level_services': [
            {
                'id': 'accelerator',
                'name': 'Accelerator',
                'description': 'Global endpoint optimization',
                'price_per_hour': 0.025,
                'price_per_gb': 0.008,
                'unit': 'per accelerator-hour + GB transfer'
            },
            {
                'id': 'accelerator_custom_routing',
                'name': 'Custom Routing Accelerator',
                'description': 'Port mapping accelerator',
                'price_per_hour': 0.025,
                'price_per_gb': 0.008,
                'unit': 'per accelerator-hour + GB transfer'
            },
            {
                'id': 'accelerator_flow_logs',
                'name': 'Accelerator Flow Logs',
                'description': 'Traffic flow logs',
                'price_per_gb': 0.03,
                'unit': 'per GB processed'
            }
        ]
    },
    
    'route53': {
        'name': 'Route 53',
        'low_level_services': [
            {
                'id': 'hosted_zone',
                'name': 'Hosted Zone',
                'description': 'DNS namespace management',
                'price_per_month': 0.50,
                'unit': 'per zone-month'
            },
            {
                'id': 'hosted_zone_private',
                'name': 'Private Hosted Zone',
                'description': 'Internal DNS namespace',
                'price_per_month': 0.50,
                'unit': 'per zone-month'
            },
            {
                'id': 'dns_query',
                'name': 'DNS Queries',
                'description': 'DNS resolution requests',
                'price_per_million': 0.40,
                'unit': 'per million queries'
            },
            {
                'id': 'health_check',
                'name': 'Basic Health Check',
                'description': 'Endpoint monitoring',
                'price_per_month': 0.50,
                'unit': 'per check-month'
            },
            {
                'id': 'health_check_enhanced',
                'name': 'Enhanced Health Check',
                'description': 'Advanced endpoint monitoring',
                'price_per_month': 2.00,
                'unit': 'per check-month'
            },
            {
                'id': 'health_check_https',
                'name': 'HTTPS Health Check',
                'description': 'SSL/TLS endpoint monitoring',
                'price_per_month': 1.00,
                'unit': 'per check-month'
            },
            {
                'id': 'health_check_string_match',
                'name': 'String Match Health Check',
                'description': 'Content validation monitoring',
                'price_per_month': 1.00,
                'unit': 'per check-month'
            },
            {
                'id': 'dns_firewall',
                'name': 'DNS Firewall',
                'description': 'DNS query filtering',
                'price_per_list_month': 0.60,
                'price_per_million_queries': 0.40,
                'unit': 'per domain list-month + per million queries'
            },
            {
                'id': 'query_logging',
                'name': 'Query Logging',
                'description': 'DNS query audit logs',
                'price_per_gb': 0.50,
                'unit': 'per GB logged'
            },
            {
                'id': 'resolver_inbound_endpoint',
                'name': 'Resolver Inbound Endpoint',
                'description': 'DNS resolution for on-premises',
                'price_per_hour': 0.125,
                'unit': 'per endpoint-hour'
            },
            {
                'id': 'resolver_outbound_endpoint',
                'name': 'Resolver Outbound Endpoint',
                'description': 'Conditional forwarding to on-premises',
                'price_per_hour': 0.125,
                'unit': 'per endpoint-hour'
            },
            {
                'id': 'resolver_rule',
                'name': 'Resolver Rule',
                'description': 'Conditional forwarding rules',
                'price_per_rule_month': 0.00,
                'unit': 'free'
            },
            {
                'id': 'resolver_rule_association',
                'name': 'Resolver Rule Association',
                'description': 'Rule to VPC binding',
                'price_per_association_month': 0.00,
                'unit': 'free'
            },
            {
                'id': 'traffic_flow',
                'name': 'Traffic Flow',
                'description': 'Visual traffic policy editor',
                'price_per_policy_month': 50.00,
                'unit': 'per policy-month'
            },
            {
                'id': 'domain_registration',
                'name': 'Domain Registration',
                'description': 'Domain name registration',
                'price_per_year': 12.00,
                'unit': 'per domain-year (varies by TLD)'
            },
            {
                'id': 'domain_transfer',
                'name': 'Domain Transfer',
                'description': 'Domain transfer in',
                'price_per_transfer': 10.00,
                'unit': 'per domain (varies by TLD)'
            },
            {
                'id': 'domain_privacy',
                'name': 'Domain Privacy Protection',
                'description': 'WHOIS privacy',
                'price_per_year': 6.00,
                'unit': 'per domain-year'
            },
            {
                'id': 'geo_location',
                'name': 'Geolocation Routing',
                'description': 'Location-based DNS routing',
                'price_per_month': 0.00,
                'unit': 'free'
            },
            {
                'id': 'latency_routing',
                'name': 'Latency Routing',
                'description': 'Low-latency DNS routing',
                'price_per_month': 0.00,
                'unit': 'free'
            },
            {
                'id': 'weighted_routing',
                'name': 'Weighted Routing',
                'description': 'Traffic distribution routing',
                'price_per_month': 0.00,
                'unit': 'free'
            },
            {
                'id': 'failover_routing',
                'name': 'Failover Routing',
                'description': 'Disaster recovery routing',
                'price_per_month': 0.00,
                'unit': 'free'
            },
            {
                'id': 'multivalue_routing',
                'name': 'Multi-Value Answer Routing',
                'description': 'Random response routing',
                'price_per_month': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'cloudfront': {
        'name': 'CloudFront',
        'low_level_services': [
            {
                'id': 'distribution',
                'name': 'Distribution',
                'description': 'CDN configuration',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'data_transfer_out',
                'name': 'Data Transfer Out',
                'description': 'Content delivery to internet',
                'price_per_gb': 0.085,
                'unit': 'per GB (varies by region)'
            },
            {
                'id': 'http_requests',
                'name': 'HTTP/HTTPS Requests',
                'description': 'Content requests',
                'price_per_10k': 0.0075,
                'unit': 'per 10,000 requests'
            },
            {
                'id': 'field_level_encryption',
                'name': 'Field-Level Encryption',
                'description': 'Sensitive data protection',
                'price_per_10k': 0.0075,
                'unit': 'per 10,000 requests'
            },
            {
                'id': 'lambda_at_edge',
                'name': 'Lambda@Edge',
                'description': 'Edge computing',
                'price_per_million': 0.60,
                'price_per_gb_second': 0.00005001,
                'unit': 'per million requests + compute'
            },
            {
                'id': 'cloudfront_functions',
                'name': 'CloudFront Functions',
                'description': 'Lightweight edge functions',
                'price_per_million': 0.10,
                'unit': 'per million invocations'
            },
            {
                'id': 'realtime_logs',
                'name': 'Real-Time Logs',
                'description': 'Instant access logs',
                'price_per_gb': 0.0075,
                'unit': 'per GB processed'
            },
            {
                'id': 'origin_shield',
                'name': 'Origin Shield',
                'description': 'Centralized cache layer',
                'price_per_10k': 0.0075,
                'unit': 'per 10,000 requests'
            },
            {
                'id': 'ssl_certificate',
                'name': 'SSL/TLS Certificate',
                'description': 'HTTPS termination',
                'price_per_month': 0.00,
                'unit': 'free (ACM)'
            },
            {
                'id': 'invalidation',
                'name': 'Cache Invalidation',
                'description': 'Content invalidation requests',
                'price_per_path_month': 0.005,
                'unit': 'per path (first 1,000 free)'
            }
        ]
    },
    
    'apigateway': {
        'name': 'API Gateway',
        'low_level_services': [
            {
                'id': 'api_requests',
                'name': 'REST API Requests',
                'description': 'RESTful endpoint invocations',
                'price_per_million': 3.50,
                'price_per_gb': 0.09,
                'unit': 'per million requests + data transfer'
            },
            {
                'id': 'http_api_requests',
                'name': 'HTTP API Requests',
                'description': 'HTTP endpoint invocations',
                'price_per_million': 1.00,
                'price_per_gb': 0.09,
                'unit': 'per million requests + data transfer'
            },
            {
                'id': 'websocket_messages',
                'name': 'WebSocket Messages',
                'description': 'Real-time bidirectional messages',
                'price_per_million': 1.00,
                'unit': 'per million messages'
            },
            {
                'id': 'websocket_connection',
                'name': 'WebSocket Connection',
                'description': 'Active connection duration',
                'price_per_connection_minute': 0.00000139,
                'unit': 'per connection-minute'
            },
            {
                'id': 'api_caching_small',
                'name': 'Cache - 0.5GB',
                'description': 'Response caching',
                'price_per_hour': 0.020,
                'unit': 'per hour'
            },
            {
                'id': 'api_caching_medium',
                'name': 'Cache - 1.6GB',
                'description': 'Response caching',
                'price_per_hour': 0.038,
                'unit': 'per hour'
            },
            {
                'id': 'api_caching_large',
                'name': 'Cache - 6.1GB',
                'description': 'Response caching',
                'price_per_hour': 0.148,
                'unit': 'per hour'
            },
            {
                'id': 'api_caching_xlarge',
                'name': 'Cache - 13.5GB',
                'description': 'Response caching',
                'price_per_hour': 0.298,
                'unit': 'per hour'
            },
            {
                'id': 'api_caching_2xlarge',
                'name': 'Cache - 28.4GB',
                'description': 'Response caching',
                'price_per_hour': 0.608,
                'unit': 'per hour'
            },
            {
                'id': 'api_caching_4xlarge',
                'name': 'Cache - 58.2GB',
                'description': 'Response caching',
                'price_per_hour': 1.208,
                'unit': 'per hour'
            },
            {
                'id': 'api_caching_8xlarge',
                'name': 'Cache - 118GB',
                'description': 'Response caching',
                'price_per_hour': 2.408,
                'unit': 'per hour'
            },
            {
                'id': 'api_gateway_throttling',
                'name': 'Usage Plans & API Keys',
                'description': 'Client throttling',
                'price_per_month': 0.00,
                'unit': 'free'
            },
            {
                'id': 'api_gateway_custom_domain',
                'name': 'Custom Domain Names',
                'description': 'Branded API endpoints',
                'price_per_certificate_month': 0.00,
                'unit': 'free (ACM billed)'
            },
            {
                'id': 'api_gateway_canary',
                'name': 'Canary Deployments',
                'description': 'Staged rollouts',
                'price_per_deployment': 0.00,
                'unit': 'free'
            },
            {
                'id': 'api_gateway_authorizer',
                'name': 'Lambda Authorizers',
                'description': 'Custom authentication',
                'price_per_request': 0.00,
                'unit': 'Lambda pricing applies'
            }
        ]
    },
    
    'elb': {
        'name': 'Elastic Load Balancing',
        'low_level_services': [
            {
                'id': 'application_load_balancer',
                'name': 'Application Load Balancer',
                'description': 'Layer 7 load balancing',
                'price_per_hour': 0.0225,
                'price_per_lcu_hour': 0.008,
                'unit': 'per ALB-hour + LCU-hour'
            },
            {
                'id': 'network_load_balancer',
                'name': 'Network Load Balancer',
                'description': 'Layer 4 load balancing',
                'price_per_hour': 0.0225,
                'price_per_ncu_hour': 0.006,
                'unit': 'per NLB-hour + NCU-hour'
            },
            {
                'id': 'gateway_load_balancer',
                'name': 'Gateway Load Balancer',
                'description': 'Third-party appliance integration',
                'price_per_hour': 0.0125,
                'price_per_gwlb_hour': 0.0035,
                'unit': 'per GWLB-hour + GLCU-hour'
            },
            {
                'id': 'classic_load_balancer',
                'name': 'Classic Load Balancer',
                'description': 'Legacy load balancing',
                'price_per_hour': 0.025,
                'price_per_gb': 0.008,
                'unit': 'per CLB-hour + GB processed'
            }
        ]
    },
    
    'vpc_lattice': {
        'name': 'VPC Lattice',
        'low_level_services': [
            {
                'id': 'vpc_lattice_service',
                'name': 'VPC Lattice Service',
                'description': 'Service-to-service connectivity',
                'price_per_hour': 0.025,
                'price_per_gb': 0.025,
                'unit': 'per service-hour + GB processed'
            },
            {
                'id': 'vpc_lattice_target_group',
                'name': 'VPC Lattice Target Group',
                'description': 'Resource grouping',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'vpc_lattice_listener',
                'name': 'VPC Lattice Listener',
                'description': 'Traffic endpoints',
                'price_per_hour': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'privatelink': {
        'name': 'AWS PrivateLink',
        'low_level_services': [
            {
                'id': 'vpc_endpoint_interface',
                'name': 'Interface VPC Endpoint',
                'description': 'Private connectivity to services',
                'price_per_hour': 0.01,
                'price_per_gb': 0.01,
                'unit': 'per endpoint-hour + GB processed'
            },
            {
                'id': 'vpc_endpoint_gateway',
                'name': 'Gateway VPC Endpoint',
                'description': 'S3/DynamoDB private access',
                'price_per_hour': 0.00,
                'price_per_gb': 0.00,
                'unit': 'free'
            },
            {
                'id': 'endpoint_service',
                'name': 'Endpoint Service (NLB)',
                'description': 'Your service in PrivateLink',
                'price_per_hour': 0.01,
                'price_per_gb': 0.01,
                'unit': 'per service-hour + GB processed'
            }
        ]
    },
    
    'transit_gateway': {
        'name': 'Transit Gateway',
        'low_level_services': [
            {
                'id': 'transit_gateway',
                'name': 'Transit Gateway',
                'description': 'Hub-and-spoke networking',
                'price_per_hour': 0.05,
                'unit': 'per gateway-hour'
            },
            {
                'id': 'transit_gateway_attachment_vpc',
                'name': 'Transit Gateway VPC Attachment',
                'description': 'VPC connection',
                'price_per_hour': 0.05,
                'unit': 'per attachment-hour'
            },
            {
                'id': 'transit_gateway_attachment_vpn',
                'name': 'Transit Gateway VPN Attachment',
                'description': 'VPN connection',
                'price_per_hour': 0.05,
                'unit': 'per attachment-hour'
            },
            {
                'id': 'transit_gateway_attachment_dx',
                'name': 'Transit Gateway Direct Connect Attachment',
                'description': 'Direct Connect connection',
                'price_per_hour': 0.05,
                'unit': 'per attachment-hour'
            },
            {
                'id': 'transit_gateway_attachment_peering',
                'name': 'Transit Gateway Peering Attachment',
                'description': 'Cross-region peering',
                'price_per_hour': 0.05,
                'unit': 'per attachment-hour'
            },
            {
                'id': 'transit_gateway_data_processed',
                'name': 'Transit Gateway Data Transfer',
                'description': 'Data processed per GB',
                'price_per_gb': 0.02,
                'unit': 'per GB (same region)'
            },
            {
                'id': 'transit_gateway_route_table',
                'name': 'Transit Gateway Route Table',
                'description': 'Route propagation and association',
                'price_per_hour': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    # ========== COMPUTE ==========
    'ec2': {
        'name': 'Elastic Compute Cloud',
        'low_level_services': [
            {
                'id': 'ebs_volume_gp3',
                'name': 'EBS General Purpose SSD (gp3)',
                'description': 'Block storage',
                'price_per_gb_month': 0.08,
                'price_per_iops_hour': 0.00004,
                'unit': 'per GB-month + IOPS-hour'
            },
            {
                'id': 'ebs_volume_gp2',
                'name': 'EBS General Purpose SSD (gp2)',
                'description': 'Block storage',
                'price_per_gb_month': 0.10,
                'unit': 'per GB-month'
            },
            {
                'id': 'ebs_volume_io1',
                'name': 'EBS Provisioned IOPS SSD (io1)',
                'description': 'High-performance block storage',
                'price_per_gb_month': 0.125,
                'price_per_iops_month': 0.065,
                'unit': 'per GB-month + IOPS-month'
            },
            {
                'id': 'ebs_volume_io2',
                'name': 'EBS Provisioned IOPS SSD (io2)',
                'description': 'High-performance block storage',
                'price_per_gb_month': 0.125,
                'price_per_iops_month': 0.065,
                'unit': 'per GB-month + IOPS-month'
            },
            {
                'id': 'ebs_volume_st1',
                'name': 'EBS Throughput Optimized HDD (st1)',
                'description': 'Frequently accessed workloads',
                'price_per_gb_month': 0.045,
                'unit': 'per GB-month'
            },
            {
                'id': 'ebs_volume_sc1',
                'name': 'EBS Cold HDD (sc1)',
                'description': 'Infrequently accessed data',
                'price_per_gb_month': 0.025,
                'unit': 'per GB-month'
            },
            {
                'id': 'ebs_volume_standard',
                'name': 'EBS Magnetic (standard)',
                'description': 'Previous generation HDD',
                'price_per_gb_month': 0.05,
                'price_per_million_ios': 0.05,
                'unit': 'per GB-month + per million I/O'
            },
            {
                'id': 'ebs_snapshot',
                'name': 'EBS Snapshots',
                'description': 'Point-in-time backups',
                'price_per_gb_month': 0.05,
                'unit': 'per GB-month'
            },
            {
                'id': 'ebs_snapshot_incremental',
                'name': 'Incremental Snapshots',
                'description': 'Changed block backups',
                'price_per_gb_month': 0.05,
                'unit': 'per GB-month (changed blocks)'
            },
            {
                'id': 'ebs_fast_snapshot_restore',
                'name': 'Fast Snapshot Restore',
                'description': 'Instant snapshot hydration',
                'price_per_gb_month': 0.15,
                'unit': 'per GB-month'
            },
            {
                'id': 'ebs_snapshot_archive',
                'name': 'Snapshot Archive',
                'description': 'Cold storage for snapshots',
                'price_per_gb_month': 0.0125,
                'unit': 'per GB-month'
            },
            {
                'id': 'ebs_recycle_bin',
                'name': 'Recycle Bin',
                'description': 'Retention of deleted snapshots',
                'price_per_gb_month': 0.05,
                'unit': 'per GB-month'
            },
            {
                'id': 'ami_storage',
                'name': 'AMI Storage',
                'description': 'Amazon Machine Images',
                'price_per_gb_month': 0.05,
                'unit': 'per GB-month'
            },
            {
                'id': 'dedicated_host',
                'name': 'Dedicated Host',
                'description': 'Physical server isolation',
                'price_per_hour': 1.00,
                'unit': 'per host-hour (approximate)'
            },
            {
                'id': 'dedicated_host_a1',
                'name': 'Dedicated Host - A1',
                'description': 'ARM-based dedicated host',
                'price_per_hour': 0.55,
                'unit': 'per host-hour'
            },
            {
                'id': 'dedicated_host_c5',
                'name': 'Dedicated Host - C5',
                'description': 'Compute optimized dedicated host',
                'price_per_hour': 1.18,
                'unit': 'per host-hour'
            },
            {
                'id': 'dedicated_host_m5',
                'name': 'Dedicated Host - M5',
                'description': 'General purpose dedicated host',
                'price_per_hour': 1.30,
                'unit': 'per host-hour'
            },
            {
                'id': 'dedicated_host_r5',
                'name': 'Dedicated Host - R5',
                'description': 'Memory optimized dedicated host',
                'price_per_hour': 1.58,
                'unit': 'per host-hour'
            },
            {
                'id': 'dedicated_host_placement_group',
                'name': 'Dedicated Host Placement Group',
                'description': 'High availability grouping',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'capacity_reservation',
                'name': 'Capacity Reservation',
                'description': 'Reserved compute capacity',
                'price_per_hour': 0.00,
                'unit': 'instance pricing applies'
            },
            {
                'id': 'elastic_ip',
                'name': 'Elastic IP',
                'description': 'Static public IPv4',
                'price_per_hour': 0.005,
                'unit': 'per address-hour (unattached)'
            },
            {
                'id': 'ec2_spot_instance',
                'name': 'Spot Instance',
                'description': 'Spare capacity compute',
                'price_per_hour': 0.00,
                'unit': 'discounted variable pricing'
            },
            {
                'id': 'ec2_reserved_instance',
                'name': 'Reserved Instance',
                'description': 'Billing discount commitment',
                'price_per_month': 0.00,
                'unit': 'upfront + discounted hourly'
            },
            {
                'id': 'ec2_savings_plan',
                'name': 'Compute Savings Plan',
                'description': 'Flexible compute commitment',
                'price_per_hour': 0.00,
                'unit': 'committed spend discount'
            },
            {
                'id': 'ec2_launch_template',
                'name': 'Launch Template',
                'description': 'Instance configuration template',
                'price_per_version_month': 0.00,
                'unit': 'free'
            },
            {
                'id': 'placement_group',
                'name': 'Placement Group',
                'description': 'Instance placement strategy',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'ec2_metadata_service',
                'name': 'Instance Metadata Service',
                'description': 'Instance configuration data',
                'price_per_request': 0.00,
                'unit': 'free'
            },
            {
                'id': 'ec2_serial_console',
                'name': 'EC2 Serial Console',
                'description': 'Out-of-band instance access',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'ec2_instance_connect',
                'name': 'EC2 Instance Connect',
                'description': 'SSH keyless access',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'ec2_optimized_ebs',
                'name': 'EBS Optimized Instance',
                'description': 'Dedicated EBS bandwidth',
                'price_per_hour': 0.00,
                'unit': 'included in newer instances'
            },
            {
                'id': 'ec2_enhanced_networking',
                'name': 'Enhanced Networking',
                'description': 'SR-IOV networking',
                'price_per_hour': 0.00,
                'unit': 'free with supported instances'
            },
            {
                'id': 'ec2_efa',
                'name': 'Elastic Fabric Adapter',
                'description': 'HPC/ML low-latency networking',
                'price_per_hour': 0.00,
                'unit': 'instance pricing applies'
            },
            {
                'id': 'ec2_cpu_credits',
                'name': 'CPU Credits',
                'description': 'T3/T4g burst credits',
                'price_per_credit': 0.05,
                'unit': 'per vCPU-hour credit'
            },
            {
                'id': 'ec2_license_included',
                'name': 'License Included Windows',
                'description': 'Windows Server license',
                'price_per_hour': 0.04,
                'unit': 'per hour (additional)'
            }
        ]
    },
    
    'lambda': {
        'name': 'Lambda',
        'low_level_services': [
            {
                'id': 'lambda_execution',
                'name': 'Execution Time',
                'description': 'Compute duration',
                'price_per_gb_second': 0.0000166667,
                'unit': 'per GB-second'
            },
            {
                'id': 'lambda_requests',
                'name': 'Requests',
                'description': 'Invocation count',
                'price_per_million': 0.20,
                'unit': 'per million requests'
            },
            {
                'id': 'lambda_provisioned_concurrency',
                'name': 'Provisioned Concurrency',
                'description': 'Pre-initialized instances',
                'price_per_gb_second': 0.0000041667,
                'unit': 'per GB-second'
            },
            {
                'id': 'lambda_layers',
                'name': 'Layers',
                'description': 'Shared code/resources',
                'price_per_gb_second': 0.00000099,
                'unit': 'per GB-second'
            },
            {
                'id': 'lambda_duration_x86',
                'name': 'Execution Time (x86)',
                'description': 'x86 compute duration',
                'price_per_gb_second': 0.0000166667,
                'unit': 'per GB-second'
            },
            {
                'id': 'lambda_duration_arm',
                'name': 'Execution Time (Arm/Graviton)',
                'description': 'ARM compute duration',
                'price_per_gb_second': 0.0000133333,
                'unit': 'per GB-second (20% less)'
            },
            {
                'id': 'lambda_arm_requests',
                'name': 'Requests (Arm)',
                'description': 'ARM invocation count',
                'price_per_million': 0.16,
                'unit': 'per million requests'
            },
            {
                'id': 'lambda_ephemeral_storage',
                'name': 'Ephemeral Storage',
                'description': '/tmp directory',
                'price_per_gb_second': 0.0000000309,
                'unit': 'per GB-second'
            },
            {
                'id': 'lambda_response_streaming',
                'name': 'Response Streaming',
                'description': 'Streaming responses',
                'price_per_gb': 0.00,
                'unit': 'billed as standard execution'
            },
            {
                'id': 'lambda_code_signing',
                'name': 'Code Signing',
                'description': 'Code verification',
                'price_per_profile_month': 0.05,
                'unit': 'per signing profile-month'
            },
            {
                'id': 'lambda_public_layers',
                'name': 'Public Layers',
                'description': 'Shared community layers',
                'price_per_gb': 0.00,
                'unit': 'free'
            },
            {
                'id': 'lambda_function_url',
                'name': 'Function URLs',
                'description': 'HTTPS endpoints',
                'price_per_request': 0.00,
                'unit': 'billed as requests'
            },
            {
                'id': 'lambda_aliases',
                'name': 'Aliases',
                'description': 'Version pointers',
                'price_per_alias': 0.00,
                'unit': 'free'
            },
            {
                'id': 'lambda_versions',
                'name': 'Versions',
                'description': 'Immutable code versions',
                'price_per_version': 0.00,
                'unit': 'free'
            },
            {
                'id': 'lambda_environment_variables',
                'name': 'Environment Variables',
                'description': 'Runtime configuration',
                'price_per_kb': 0.00,
                'unit': 'free'
            },
            {
                'id': 'lambda_event_source_mapping',
                'name': 'Event Source Mapping',
                'description': 'Stream/queue integrations',
                'price_per_mapping': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'ecs': {
        'name': 'Elastic Container Service',
        'low_level_services': [
            {
                'id': 'ecs_fargate_vcpu',
                'name': 'Fargate vCPU',
                'description': 'Serverless container compute',
                'price_per_vcpu_hour': 0.04048,
                'unit': 'per vCPU-hour'
            },
            {
                'id': 'ecs_fargate_memory',
                'name': 'Fargate Memory',
                'description': 'Serverless container memory',
                'price_per_gb_hour': 0.0044452,
                'unit': 'per GB-hour'
            },
            {
                'id': 'ecs_fargate_ephemeral_storage',
                'name': 'Fargate Ephemeral Storage',
                'description': 'Container scratch space',
                'price_per_gb_hour': 0.000111,
                'unit': 'per GB-hour (20GB free)'
            },
            {
                'id': 'ecs_fargate_x86',
                'name': 'Fargate x86',
                'description': 'x86 compute',
                'price_per_vcpu_hour': 0.04048,
                'price_per_gb_hour': 0.0044452,
                'unit': 'per vCPU-hour + GB-hour'
            },
            {
                'id': 'ecs_fargate_arm',
                'name': 'Fargate Arm/Graviton',
                'description': 'ARM compute',
                'price_per_vcpu_hour': 0.03238,
                'price_per_gb_hour': 0.0035562,
                'unit': 'per vCPU-hour + GB-hour (20% less)'
            },
            {
                'id': 'ecs_service_discovery',
                'name': 'Service Discovery',
                'description': 'DNS-based service discovery',
                'price_per_service_month': 0.50,
                'unit': 'per service-month'
            },
            {
                'id': 'ecs_execute_command',
                'name': 'Execute Command',
                'description': 'Interactive container access',
                'price_per_gb': 0.25,
                'price_per_gb_out': 0.25,
                'unit': 'per GB in/out'
            },
            {
                'id': 'ecs_capacity_provider',
                'name': 'Capacity Provider',
                'description': 'Infrastructure provisioning',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'ecs_task_definition',
                'name': 'Task Definition',
                'description': 'Container blueprint',
                'price_per_revision': 0.00,
                'unit': 'free'
            },
            {
                'id': 'ecs_task_role',
                'name': 'IAM Task Role',
                'description': 'Container permissions',
                'price_per_role': 0.00,
                'unit': 'free (IAM free)'
            },
            {
                'id': 'ecs_awsvpc_network',
                'name': 'awsvpc Network Mode',
                'description': 'Enhanced networking',
                'price_per_hour': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'eks': {
        'name': 'Elastic Kubernetes Service',
        'low_level_services': [
            {
                'id': 'eks_control_plane',
                'name': 'EKS Control Plane',
                'description': 'Managed Kubernetes control plane',
                'price_per_hour': 0.10,
                'unit': 'per cluster-hour'
            },
            {
                'id': 'eks_fargate_vcpu',
                'name': 'EKS Fargate vCPU',
                'description': 'Serverless pods compute',
                'price_per_vcpu_hour': 0.04048,
                'unit': 'per vCPU-hour'
            },
            {
                'id': 'eks_fargate_memory',
                'name': 'EKS Fargate Memory',
                'description': 'Serverless pods memory',
                'price_per_gb_hour': 0.0044452,
                'unit': 'per GB-hour'
            },
            {
                'id': 'eks_fargate_arm',
                'name': 'EKS Fargate Arm',
                'description': 'Graviton serverless pods',
                'price_per_vcpu_hour': 0.03238,
                'price_per_gb_hour': 0.0035562,
                'unit': 'per vCPU-hour + GB-hour'
            },
            {
                'id': 'eks_managed_node_group',
                'name': 'Managed Node Group',
                'description': 'EC2 worker node management',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'eks_add_on',
                'name': 'EKS Add-ons',
                'description': 'Kubernetes add-ons',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'eks_control_plane_logging',
                'name': 'Control Plane Logging',
                'description': 'Audit/diagnostic logs',
                'price_per_gb': 0.80,
                'unit': 'per GB (CloudWatch)'
            },
            {
                'id': 'eks_cluster_auto_scaler',
                'name': 'Cluster Auto Scaler',
                'description': 'Automatic node scaling',
                'price_per_hour': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'elastic_beanstalk': {
        'name': 'Elastic Beanstalk',
        'low_level_services': [
            {
                'id': 'ebs_custom_platform',
                'name': 'Custom Platform',
                'description': 'Custom runtime environment',
                'price_per_instance_hour': 0.10,
                'unit': 'per instance-hour platform fee'
            },
            {
                'id': 'ebs_application_version',
                'name': 'Application Version',
                'description': 'Source bundle storage',
                'price_per_gb_month': 0.023,
                'unit': 'per GB-month (S3)'
            },
            {
                'id': 'ebs_environment',
                'name': 'Environment',
                'description': 'Application environment',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'ebs_managed_update',
                'name': 'Managed Updates',
                'description': 'Automatic platform updates',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'ebs_saved_config',
                'name': 'Saved Configuration',
                'description': 'Environment templates',
                'price_per_config': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'batch': {
        'name': 'AWS Batch',
        'low_level_services': [
            {
                'id': 'batch_compute_environment',
                'name': 'Compute Environment',
                'description': 'Job compute infrastructure',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'batch_job_queue',
                'name': 'Job Queue',
                'description': 'Job scheduling queue',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'batch_job_definition',
                'name': 'Job Definition',
                'description': 'Job blueprint',
                'price_per_revision': 0.00,
                'unit': 'free'
            },
            {
                'id': 'batch_fargate_vcpu',
                'name': 'Batch Fargate vCPU',
                'description': 'Serverless job compute',
                'price_per_vcpu_hour': 0.04048,
                'unit': 'per vCPU-hour'
            },
            {
                'id': 'batch_fargate_memory',
                'name': 'Batch Fargate Memory',
                'description': 'Serverless job memory',
                'price_per_gb_hour': 0.0044452,
                'unit': 'per GB-hour'
            }
        ]
    },
    
    # ========== STORAGE ==========
    's3': {
        'name': 'Simple Storage Service',
        'low_level_services': [
            {
                'id': 's3_standard_storage',
                'name': 'S3 Standard',
                'description': 'Frequently accessed data',
                'price_per_gb_month': 0.023,
                'unit': 'per GB-month'
            },
            {
                'id': 's3_intelligent_tiering',
                'name': 'S3 Intelligent-Tiering',
                'description': 'Automatic cost optimization',
                'price_per_gb_month': 0.0025,
                'price_per_thousand_objects': 0.0025,
                'unit': 'per GB-month + per 1000 objects'
            },
            {
                'id': 's3_standard_ia',
                'name': 'S3 Standard-IA',
                'description': 'Infrequent access',
                'price_per_gb_month': 0.0125,
                'price_per_gb': 0.01,
                'unit': 'per GB-month + retrieval'
            },
            {
                'id': 's3_onezone_ia',
                'name': 'S3 One Zone-IA',
                'description': 'Recreated data, infrequent',
                'price_per_gb_month': 0.01,
                'price_per_gb': 0.01,
                'unit': 'per GB-month + retrieval'
            },
            {
                'id': 's3_glacier_instant',
                'name': 'S3 Glacier Instant Retrieval',
                'description': 'Long-term, millisecond access',
                'price_per_gb_month': 0.004,
                'price_per_gb': 0.01,
                'unit': 'per GB-month + retrieval'
            },
            {
                'id': 's3_glacier_flexible',
                'name': 'S3 Glacier Flexible Retrieval',
                'description': 'Archive, minutes-hours',
                'price_per_gb_month': 0.0036,
                'price_per_gb': 0.01,
                'unit': 'per GB-month + retrieval'
            },
            {
                'id': 's3_glacier_deep_archive',
                'name': 'S3 Glacier Deep Archive',
                'description': 'Long-term archive, hours',
                'price_per_gb_month': 0.00099,
                'price_per_gb': 0.02,
                'unit': 'per GB-month + retrieval'
            },
            {
                'id': 's3_put_requests',
                'name': 'PUT/COPY/POST/LIST Requests',
                'description': 'Write operations',
                'price_per_thousand': 0.005,
                'unit': 'per 1,000 requests'
            },
            {
                'id': 's3_get_requests',
                'name': 'GET/SELECT Requests',
                'description': 'Read operations',
                'price_per_thousand': 0.0004,
                'unit': 'per 1,000 requests'
            },
            {
                'id': 's3_lifecycle_transition',
                'name': 'Lifecycle Transitions',
                'description': 'Storage class changes',
                'price_per_thousand': 0.01,
                'unit': 'per 1,000 transitions'
            },
            {
                'id': 's3_versioning',
                'name': 'Versioning',
                'description': 'Object version storage',
                'price_per_gb_month': 0.023,
                'unit': 'per GB-month (all versions)'
            },
            {
                'id': 's3_replication',
                'name': 'S3 Replication',
                'description': 'Cross-region/account replication',
                'price_per_gb': 0.02,
                'unit': 'per GB replicated'
            },
            {
                'id': 's3_transfer_acceleration',
                'name': 'Transfer Acceleration',
                'description': 'Fast CloudFront uploads',
                'price_per_gb': 0.04,
                'unit': 'per GB transferred'
            },
            {
                'id': 's3_inventory',
                'name': 'Inventory',
                'description': 'Object inventory reports',
                'price_per_million_objects': 0.0025,
                'unit': 'per million objects'
            },
            {
                'id': 's3_select',
                'name': 'S3 Select',
                'description': 'Server-side filtering',
                'price_per_gb_scanned': 0.002,
                'price_per_gb_returned': 0.0007,
                'unit': 'per GB scanned + GB returned'
            },
            {
                'id': 's3_object_lambda',
                'name': 'Object Lambda',
                'description': 'Real-time transformation',
                'price_per_gb_processed': 0.0000167,
                'price_per_request': 0.00,
                'unit': 'per GB processed + Lambda'
            },
            {
                'id': 's3_batch_operations',
                'name': 'Batch Operations',
                'description': 'Bulk object operations',
                'price_per_job': 0.25,
                'price_per_object': 0.001,
                'unit': 'per job + per object'
            },
            {
                'id': 's3_storage_lens',
                'name': 'Storage Lens',
                'description': 'Storage analytics',
                'price_per_million_objects': 0.20,
                'unit': 'per million objects-month'
            },
            {
                'id': 's3_access_points',
                'name': 'Access Points',
                'description': 'Shared dataset access',
                'price_per_thousand': 0.00,
                'unit': 'free'
            },
            {
                'id': 's3_multi_region_access_point',
                'name': 'Multi-Region Access Point',
                'description': 'Global endpoint',
                'price_per_gb': 0.02,
                'price_per_10k_requests': 0.0083,
                'unit': 'per GB transferred + per 10k requests'
            },
            {
                'id': 's3_outposts',
                'name': 'S3 on Outposts',
                'description': 'On-premises S3',
                'price_per_gb_month': 0.00,
                'unit': 'Outposts pricing applies'
            },
            {
                'id': 's3_object_lock',
                'name': 'Object Lock',
                'description': 'WORM compliance',
                'price_per_gb_month': 0.00,
                'unit': 'storage class pricing applies'
            }
        ]
    },
    
    'efs': {
        'name': 'Elastic File System',
        'low_level_services': [
            {
                'id': 'efs_standard',
                'name': 'EFS Standard',
                'description': 'Multi-AZ file storage',
                'price_per_gb_month': 0.30,
                'unit': 'per GB-month'
            },
            {
                'id': 'efs_ia',
                'name': 'EFS Infrequent Access',
                'description': 'Infrequently accessed files',
                'price_per_gb_month': 0.025,
                'price_per_gb': 0.01,
                'unit': 'per GB-month + retrieval'
            },
            {
                'id': 'efs_onezone',
                'name': 'EFS One Zone',
                'description': 'Single AZ file storage',
                'price_per_gb_month': 0.16,
                'unit': 'per GB-month'
            },
            {
                'id': 'efs_onezone_ia',
                'name': 'EFS One Zone-IA',
                'description': 'Single AZ, infrequent',
                'price_per_gb_month': 0.013,
                'price_per_gb': 0.01,
                'unit': 'per GB-month + retrieval'
            },
            {
                'id': 'efs_throughput',
                'name': 'EFS Provisioned Throughput',
                'description': 'Guaranteed throughput',
                'price_per_mbps_month': 6.00,
                'unit': 'per MB/s-month'
            }
        ]
    },
    
    'fsx': {
        'name': 'FSx',
        'low_level_services': [
            {
                'id': 'fsx_lustre',
                'name': 'FSx for Lustre',
                'description': 'High-performance computing',
                'price_per_gb_month': 0.145,
                'price_per_mbps_month': 1.44,
                'unit': 'per GB-month + MB/s-month'
            },
            {
                'id': 'fsx_windows',
                'name': 'FSx for Windows',
                'description': 'Windows file server',
                'price_per_gb_month': 0.12,
                'price_per_mbps_month': 2.00,
                'unit': 'per GB-month + MB/s-month'
            },
            {
                'id': 'fsx_ontap',
                'name': 'FSx for NetApp ONTAP',
                'description': 'NetApp file storage',
                'price_per_gb_month': 0.14,
                'price_per_iops_month': 0.045,
                'unit': 'per GB-month + IOPS-month'
            },
            {
                'id': 'fsx_openzfs',
                'name': 'FSx for OpenZFS',
                'description': 'ZFS file system',
                'price_per_gb_month': 0.12,
                'price_per_iops_month': 0.045,
                'unit': 'per GB-month + IOPS-month'
            },
            {
                'id': 'fsx_file_caches',
                'name': 'FSx File Cache',
                'description': 'Hybrid storage caching',
                'price_per_gb_month': 0.20,
                'price_per_mbps_month': 2.00,
                'unit': 'per GB-month + MB/s-month'
            }
        ]
    },
    
    'ebs': {
        'name': 'Elastic Block Store',
        'low_level_services': [
            {
                'id': 'ebs_gp3',
                'name': 'gp3 Volume',
                'description': 'General Purpose SSD',
                'price_per_gb_month': 0.08,
                'price_per_iops_hour': 0.00004,
                'unit': 'per GB-month + IOPS-hour'
            },
            {
                'id': 'ebs_gp2',
                'name': 'gp2 Volume',
                'description': 'General Purpose SSD',
                'price_per_gb_month': 0.10,
                'unit': 'per GB-month'
            },
            {
                'id': 'ebs_io1',
                'name': 'io1 Volume',
                'description': 'Provisioned IOPS SSD',
                'price_per_gb_month': 0.125,
                'price_per_iops_month': 0.065,
                'unit': 'per GB-month + IOPS-month'
            },
            {
                'id': 'ebs_io2',
                'name': 'io2 Block Express',
                'description': 'High-performance SSD',
                'price_per_gb_month': 0.125,
                'price_per_iops_month': 0.065,
                'unit': 'per GB-month + IOPS-month'
            },
            {
                'id': 'ebs_st1',
                'name': 'st1 Volume',
                'description': 'Throughput Optimized HDD',
                'price_per_gb_month': 0.045,
                'unit': 'per GB-month'
            },
            {
                'id': 'ebs_sc1',
                'name': 'sc1 Volume',
                'description': 'Cold HDD',
                'price_per_gb_month': 0.025,
                'unit': 'per GB-month'
            },
            {
                'id': 'ebs_snapshot',
                'name': 'EBS Snapshot',
                'description': 'Volume backups',
                'price_per_gb_month': 0.05,
                'unit': 'per GB-month'
            },
            {
                'id': 'ebs_snapshot_archive',
                'name': 'Snapshot Archive',
                'description': 'Cold snapshot storage',
                'price_per_gb_month': 0.0125,
                'unit': 'per GB-month'
            },
            {
                'id': 'ebs_fast_snapshot_restore',
                'name': 'Fast Snapshot Restore',
                'description': 'Instant hydration',
                'price_per_gb_month': 0.15,
                'unit': 'per GB-month'
            }
        ]
    },
    
    'storage_gateway': {
        'name': 'Storage Gateway',
        'low_level_services': [
            {
                'id': 'gateway_file_s3',
                'name': 'File Gateway',
                'description': 'S3 file interface',
                'price_per_gb_month': 0.023,
                'price_per_gateway_month': 125.00,
                'unit': 'per GB-month + per gateway-month'
            },
            {
                'id': 'gateway_volume',
                'name': 'Volume Gateway',
                'description': 'Block storage caching',
                'price_per_gb_month': 0.05,
                'price_per_gateway_month': 125.00,
                'unit': 'per GB-month + per gateway-month'
            },
            {
                'id': 'gateway_tape',
                'name': 'Tape Gateway',
                'description': 'Virtual tape library',
                'price_per_gb_month': 0.005,
                'price_per_gateway_month': 125.00,
                'unit': 'per GB-month + per gateway-month'
            }
        ]
    },
    
    'backup': {
        'name': 'AWS Backup',
        'low_level_services': [
            {
                'id': 'backup_vault',
                'name': 'Backup Vault',
                'description': 'Backup storage container',
                'price_per_gb_month': 0.05,
                'unit': 'per GB-month'
            },
            {
                'id': 'backup_vault_lock',
                'name': 'Backup Vault Lock',
                'description': 'WORM compliance',
                'price_per_gb_month': 0.01,
                'unit': 'per GB-month'
            },
            {
                'id': 'backup_copy',
                'name': 'Cross-Region Copy',
                'description': 'Backup replication',
                'price_per_gb': 0.01,
                'unit': 'per GB copied'
            },
            {
                'id': 'backup_legal_hold',
                'name': 'Legal Hold',
                'description': 'Immutable retention',
                'price_per_gb_month': 0.01,
                'unit': 'per GB-month'
            }
        ]
    },
    
    # ========== DATABASES ==========
    'rds': {
        'name': 'Relational Database Service',
        'low_level_services': [
            {
                'id': 'rds_db_instance',
                'name': 'DB Instance',
                'description': 'Database compute',
                'price_per_hour': 0.00,
                'unit': 'varies by instance type'
            },
            {
                'id': 'rds_storage_gp2',
                'name': 'General Purpose SSD (gp2)',
                'description': 'Database storage',
                'price_per_gb_month': 0.115,
                'unit': 'per GB-month'
            },
            {
                'id': 'rds_storage_gp3',
                'name': 'General Purpose SSD (gp3)',
                'description': 'Database storage',
                'price_per_gb_month': 0.108,
                'unit': 'per GB-month'
            },
            {
                'id': 'rds_storage_io1',
                'name': 'Provisioned IOPS SSD (io1)',
                'description': 'High-performance storage',
                'price_per_gb_month': 0.125,
                'price_per_iops_month': 0.10,
                'unit': 'per GB-month + IOPS-month'
            },
            {
                'id': 'rds_backup',
                'name': 'Automated Backups',
                'description': 'Database backups',
                'price_per_gb_month': 0.095,
                'unit': 'per GB-month'
            },
            {
                'id': 'rds_snapshot',
                'name': 'Manual Snapshots',
                'description': 'User-initiated backups',
                'price_per_gb_month': 0.095,
                'unit': 'per GB-month'
            },
            {
                'id': 'rds_export',
                'name': 'Snapshot Export',
                'description': 'Export to S3',
                'price_per_gb': 0.01,
                'unit': 'per GB exported'
            },
            {
                'id': 'rds_performance_insights',
                'name': 'Performance Insights',
                'description': 'Database monitoring',
                'price_per_hour': 0.10,
                'unit': 'per instance-hour'
            },
            {
                'id': 'rds_proxy',
                'name': 'RDS Proxy',
                'description': 'Connection pooling',
                'price_per_hour': 0.015,
                'price_per_vcpu_hour': 0.004,
                'unit': 'per proxy-hour + vCPU-hour'
            },
            {
                'id': 'rds_read_replica',
                'name': 'Read Replica',
                'description': 'Read scaling',
                'price_per_hour': 0.00,
                'unit': 'same as DB instance pricing'
            },
            {
                'id': 'rds_multi_az',
                'name': 'Multi-AZ',
                'description': 'High availability',
                'price_per_hour': 0.00,
                'unit': '2x instance pricing'
            },
            {
                'id': 'rds_reserved_instance',
                'name': 'Reserved Instance',
                'description': 'Billing discount',
                'price_per_hour': 0.00,
                'unit': '~30-60% off on-demand'
            },
            {
                'id': 'rds_parameter_group',
                'name': 'Parameter Group',
                'description': 'Database configuration',
                'price_per_group': 0.00,
                'unit': 'free'
            },
            {
                'id': 'rds_option_group',
                'name': 'Option Group',
                'description': 'Additional features',
                'price_per_group': 0.00,
                'unit': 'free'
            },
            {
                'id': 'rds_subnet_group',
                'name': 'Subnet Group',
                'description': 'Network placement',
                'price_per_group': 0.00,
                'unit': 'free'
            },
            {
                'id': 'rds_blue_green_deployment',
                'name': 'Blue/Green Deployment',
                'description': 'Safe database updates',
                'price_per_hour': 0.00,
                'unit': 'staging instance billed'
            },
            {
                'id': 'rds_aurora_backtrack',
                'name': 'Aurora Backtrack',
                'description': 'Point-in-time rollback',
                'price_per_gb_month': 0.020,
                'unit': 'per GB-month of change records'
            },
            {
                'id': 'rds_aurora_parallel_query',
                'name': 'Aurora Parallel Query',
                'description': 'Analytics acceleration',
                'price_per_gb_scanned': 0.12,
                'unit': 'per TB scanned (0.12/TB)'
            }
        ]
    },
    
    'dynamodb': {
        'name': 'DynamoDB',
        'low_level_services': [
            {
                'id': 'dynamodb_wcu',
                'name': 'Write Capacity Unit',
                'description': 'Provisioned writes',
                'price_per_wcu_hour': 0.00065,
                'unit': 'per WCU-hour'
            },
            {
                'id': 'dynamodb_rcu',
                'name': 'Read Capacity Unit',
                'description': 'Provisioned reads',
                'price_per_rcu_hour': 0.00013,
                'unit': 'per RCU-hour'
            },
            {
                'id': 'dynamodb_on_demand_write',
                'name': 'On-Demand Writes',
                'description': 'Serverless writes',
                'price_per_million': 1.25,
                'unit': 'per million write requests'
            },
            {
                'id': 'dynamodb_on_demand_read',
                'name': 'On-Demand Reads',
                'description': 'Serverless reads',
                'price_per_million': 0.25,
                'unit': 'per million read requests'
            },
            {
                'id': 'dynamodb_storage',
                'name': 'Data Storage',
                'description': 'Table data',
                'price_per_gb_month': 0.25,
                'unit': 'per GB-month'
            },
            {
                'id': 'dynamodb_continuous_backup',
                'name': 'Continuous Backups',
                'description': 'Point-in-time recovery',
                'price_per_gb_month': 0.20,
                'unit': 'per GB-month'
            },
            {
                'id': 'dynamodb_on_demand_backup',
                'name': 'On-Demand Backups',
                'description': 'Manual backups',
                'price_per_gb_month': 0.10,
                'unit': 'per GB-month'
            },
            {
                'id': 'dynamodb_streams',
                'name': 'DynamoDB Streams',
                'description': 'Change data capture',
                'price_per_million_reads': 0.02,
                'unit': 'per million read requests'
            },
            {
                'id': 'dynamodb_dax_node',
                'name': 'DAX Node',
                'description': 'In-memory cache',
                'price_per_hour': 0.12,
                'unit': 'per node-hour'
            },
            {
                'id': 'dynamodb_dax_write',
                'name': 'DAX Write Capacity',
                'description': 'Cache writes',
                'price_per_million': 0.75,
                'unit': 'per million write requests'
            },
            {
                'id': 'dynamodb_dax_read',
                'name': 'DAX Read Capacity',
                'description': 'Cache reads',
                'price_per_million': 0.15,
                'unit': 'per million read requests'
            },
            {
                'id': 'dynamodb_global_table',
                'name': 'Global Tables',
                'description': 'Multi-region replication',
                'price_per_million_writes': 0.15,
                'unit': 'per million replicated write requests'
            },
            {
                'id': 'dynamodb_export_s3',
                'name': 'Export to S3',
                'description': 'Table export',
                'price_per_gb': 0.10,
                'unit': 'per GB exported'
            },
            {
                'id': 'dynamodb_import_s3',
                'name': 'Import from S3',
                'description': 'Table import',
                'price_per_gb': 0.15,
                'unit': 'per GB imported'
            },
            {
                'id': 'dynamodb_ttl',
                'name': 'Time to Live',
                'description': 'Automatic expiration',
                'price_per_million': 0.00,
                'unit': 'free'
            },
            {
                'id': 'dynamodb_transaction',
                'name': 'Transactions',
                'description': 'ACID transactions',
                'price_per_million': 2.50,
                'unit': 'per million write + read requests'
            },
            {
                'id': 'dynamodb_gsi',
                'name': 'Global Secondary Index',
                'description': 'Alternative query patterns',
                'price_per_hour': 0.00,
                'unit': 'same as table pricing'
            },
            {
                'id': 'dynamodb_lsi',
                'name': 'Local Secondary Index',
                'description': 'Scoped alternative indexes',
                'price_per_hour': 0.00,
                'unit': 'same as table pricing'
            }
        ]
    },
    
    'elasticache': {
        'name': 'ElastiCache',
        'low_level_services': [
            {
                'id': 'elasticache_node',
                'name': 'Cache Node',
                'description': 'Redis/Memcached node',
                'price_per_hour': 0.068,
                'unit': 'per node-hour (varies by type)'
            },
            {
                'id': 'elasticache_snapshot',
                'name': 'Snapshot',
                'description': 'Cache backup',
                'price_per_gb_month': 0.085,
                'unit': 'per GB-month'
            },
            {
                'id': 'elasticache_global_datastore',
                'name': 'Global Datastore',
                'description': 'Cross-region replication',
                'price_per_hour': 0.00,
                'unit': '1.5x node pricing'
            },
            {
                'id': 'elasticache_reserved_node',
                'name': 'Reserved Node',
                'description': 'Billing discount',
                'price_per_hour': 0.00,
                'unit': '~30-60% off on-demand'
            },
            {
                'id': 'elasticache_parameter_group',
                'name': 'Parameter Group',
                'description': 'Cache configuration',
                'price_per_group': 0.00,
                'unit': 'free'
            },
            {
                'id': 'elasticache_subnet_group',
                'name': 'Subnet Group',
                'description': 'Network placement',
                'price_per_group': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'redshift': {
        'name': 'Redshift',
        'low_level_services': [
            {
                'id': 'redshift_node',
                'name': 'Compute Node',
                'description': 'Data warehouse compute',
                'price_per_hour': 0.25,
                'unit': 'per node-hour (varies by type)'
            },
            {
                'id': 'redshift_spectrum',
                'name': 'Redshift Spectrum',
                'description': 'S3 querying',
                'price_per_tb': 5.00,
                'unit': 'per TB scanned'
            },
            {
                'id': 'redshift_concurrency_scaling',
                'name': 'Concurrency Scaling',
                'description': 'Query scaling',
                'price_per_second': 0.0000167,
                'unit': 'per cluster-second'
            },
            {
                'id': 'redshift_snapshot',
                'name': 'Snapshot',
                'description': 'Backup storage',
                'price_per_gb_month': 0.095,
                'unit': 'per GB-month'
            },
            {
                'id': 'redshift_managed_storage',
                'name': 'Managed Storage',
                'description': 'RA3 managed storage',
                'price_per_gb_month': 0.024,
                'unit': 'per GB-month'
            },
            {
                'id': 'redshift_aqua',
                'name': 'AQUA',
                'description': 'Hardware acceleration',
                'price_per_hour': 0.088,
                'unit': 'per cluster-hour'
            }
        ]
    },
    
    'neptune': {
        'name': 'Neptune',
        'low_level_services': [
            {
                'id': 'neptune_instance',
                'name': 'DB Instance',
                'description': 'Graph database compute',
                'price_per_hour': 0.252,
                'unit': 'per hour (varies by type)'
            },
            {
                'id': 'neptune_storage',
                'name': 'Storage',
                'description': 'Graph data storage',
                'price_per_gb_month': 0.10,
                'unit': 'per GB-month'
            },
            {
                'id': 'neptune_io',
                'name': 'I/O Requests',
                'description': 'Storage I/O',
                'price_per_million': 0.20,
                'unit': 'per million requests'
            },
            {
                'id': 'neptune_backup',
                'name': 'Backup Storage',
                'description': 'Database backups',
                'price_per_gb_month': 0.095,
                'unit': 'per GB-month'
            }
        ]
    },
    
    'docdb': {
        'name': 'DocumentDB',
        'low_level_services': [
            {
                'id': 'docdb_instance',
                'name': 'DB Instance',
                'description': 'Document database compute',
                'price_per_hour': 0.126,
                'unit': 'per hour (varies by type)'
            },
            {
                'id': 'docdb_storage',
                'name': 'Storage',
                'description': 'Document data storage',
                'price_per_gb_month': 0.10,
                'unit': 'per GB-month'
            },
            {
                'id': 'docdb_io',
                'name': 'I/O Requests',
                'description': 'Storage I/O',
                'price_per_million': 0.20,
                'unit': 'per million requests'
            },
            {
                'id': 'docdb_backup',
                'name': 'Backup Storage',
                'description': 'Database backups',
                'price_per_gb_month': 0.095,
                'unit': 'per GB-month'
            }
        ]
    },
    
    'keyspaces': {
        'name': 'Keyspaces',
        'low_level_services': [
            {
                'id': 'keyspaces_write',
                'name': 'Write Requests',
                'description': 'Cassandra-compatible writes',
                'price_per_million': 1.25,
                'unit': 'per million write requests'
            },
            {
                'id': 'keyspaces_read',
                'name': 'Read Requests',
                'description': 'Cassandra-compatible reads',
                'price_per_million': 0.50,
                'unit': 'per million read requests'
            },
            {
                'id': 'keyspaces_storage',
                'name': 'Storage',
                'description': 'Table data storage',
                'price_per_gb_month': 0.25,
                'unit': 'per GB-month'
            }
        ]
    },
    
    'qldb': {
        'name': 'QLDB',
        'low_level_services': [
            {
                'id': 'qldb_streams',
                'name': 'Journal Storage',
                'description': 'Immutable journal',
                'price_per_gb_month': 0.026,
                'unit': 'per GB-month'
            },
            {
                'id': 'qldb_indexed_storage',
                'name': 'Indexed Storage',
                'description': 'Active data storage',
                'price_per_gb_month': 0.15,
                'unit': 'per GB-month'
            },
            {
                'id': 'qldb_io',
                'name': 'Read/Write I/O',
                'description': 'Journal I/O',
                'price_per_million': 0.30,
                'unit': 'per million I/O requests'
            }
        ]
    },
    
    'timestream': {
        'name': 'Timestream',
        'low_level_services': [
            {
                'id': 'timestream_write',
                'name': 'Write Requests',
                'description': 'Time-series data writes',
                'price_per_million': 0.50,
                'unit': 'per million write requests'
            },
            {
                'id': 'timestream_query',
                'name': 'Query',
                'description': 'Data queries',
                'price_per_tb_scanned': 5.00,
                'unit': 'per TB scanned'
            },
            {
                'id': 'timestream_memory_store',
                'name': 'Memory Store',
                'description': 'Recent data',
                'price_per_gb_month': 0.12,
                'unit': 'per GB-month'
            },
            {
                'id': 'timestream_magnetic_store',
                'name': 'Magnetic Store',
                'description': 'Historical data',
                'price_per_gb_month': 0.03,
                'unit': 'per GB-month'
            }
        ]
    },
    
    # ========== ANALYTICS ==========
    'glue': {
        'name': 'Glue',
        'low_level_services': [
            {
                'id': 'glue_job',
                'name': 'Glue Job',
                'description': 'ETL processing',
                'price_per_dpu_hour': 0.44,
                'unit': 'per DPU-hour'
            },
            {
                'id': 'glue_crawler',
                'name': 'Glue Crawler',
                'description': 'Schema discovery',
                'price_per_dpu_hour': 0.44,
                'unit': 'per DPU-hour'
            },
            {
                'id': 'glue_data_catalog',
                'name': 'Data Catalog',
                'description': 'Metadata repository',
                'price_per_100k_objects': 1.00,
                'unit': 'per 100k objects-month'
            },
            {
                'id': 'glue_request',
                'name': 'Data Catalog Request',
                'description': 'Metadata operations',
                'price_per_million': 1.00,
                'unit': 'per million requests'
            },
            {
                'id': 'glue_dev_endpoint',
                'name': 'Development Endpoint',
                'description': 'Interactive development',
                'price_per_dpu_hour': 0.44,
                'unit': 'per DPU-hour'
            },
            {
                'id': 'glue_blueprint',
                'name': 'Blueprint',
                'description': 'Workflow templates',
                'price_per_blueprint': 0.00,
                'unit': 'free'
            },
            {
                'id': 'glue_schema_registry',
                'name': 'Schema Registry',
                'description': 'Schema versioning',
                'price_per_registry_month': 1.00,
                'unit': 'per registry-month'
            },
            {
                'id': 'glue_ml_transform',
                'name': 'ML Transform',
                'description': 'Deduplication/finding matches',
                'price_per_dpu_hour': 0.48,
                'unit': 'per DPU-hour'
            }
        ]
    },
    
    'emr': {
        'name': 'EMR',
        'low_level_services': [
            {
                'id': 'emr_cluster',
                'name': 'EMR Cluster',
                'description': 'Big data processing',
                'price_per_ec2_hour': 0.00,
                'unit': 'EC2 pricing + EMR premium'
            },
            {
                'id': 'emr_premium',
                'name': 'EMR Premium',
                'description': 'EMR management fee',
                'price_per_ec2_hour': 0.09,
                'unit': 'per instance-hour'
            },
            {
                'id': 'emr_serverless',
                'name': 'EMR Serverless',
                'description': 'Serverless Spark/Hive',
                'price_per_dpu_hour': 0.52,
                'unit': 'per DPU-hour'
            },
            {
                'id': 'emr_eks',
                'name': 'EMR on EKS',
                'description': 'EKS-based Spark',
                'price_per_cpu_hour': 0.01012,
                'price_per_gb_hour': 0.00111125,
                'unit': 'per vCPU-hour + GB-hour'
            }
        ]
    },
    
    'kinesis': {
        'name': 'Kinesis',
        'low_level_services': [
            {
                'id': 'kinesis_stream_shard',
                'name': 'Stream Shard',
                'description': 'Data stream capacity',
                'price_per_shard_hour': 0.015,
                'unit': 'per shard-hour'
            },
            {
                'id': 'kinesis_put_payload',
                'name': 'PUT Payload Unit',
                'description': 'Data ingestion',
                'price_per_million_units': 0.014,
                'unit': 'per million PUT payload units'
            },
            {
                'id': 'kinesis_extended_retention',
                'name': 'Extended Retention',
                'description': '7-365 day retention',
                'price_per_shard_hour': 0.020,
                'unit': 'per shard-hour'
            },
            {
                'id': 'kinesis_fanout_consumer',
                'name': 'Fan-Out Consumer',
                'description': 'Enhanced fan-out',
                'price_per_consumer_hour': 0.015,
                'price_per_gb': 0.013,
                'unit': 'per consumer-hour + GB'
            },
            {
                'id': 'kinesis_analytics',
                'name': 'Kinesis Analytics',
                'description': 'Stream processing',
                'price_per_kpu_hour': 0.11,
                'unit': 'per Kinesis Processing Unit-hour'
            }
        ]
    },
    
    'athena': {
        'name': 'Athena',
        'low_level_services': [
            {
                'id': 'athena_query',
                'name': 'Query',
                'description': 'S3 query execution',
                'price_per_tb_scanned': 5.00,
                'unit': 'per TB scanned'
            },
            {
                'id': 'athena_engine_version',
                'name': 'Engine Version',
                'description': 'Query engine',
                'price_per_version': 0.00,
                'unit': 'free'
            },
            {
                'id': 'athena_prepared_statement',
                'name': 'Prepared Statement',
                'description': 'Pre-compiled queries',
                'price_per_statement': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'msk': {
        'name': 'MSK',
        'low_level_services': [
            {
                'id': 'msk_broker',
                'name': 'Broker',
                'description': 'Kafka broker',
                'price_per_broker_hour': 0.21,
                'unit': 'per broker-hour'
            },
            {
                'id': 'msk_storage',
                'name': 'Storage',
                'description': 'Broker storage',
                'price_per_gb_month': 0.10,
                'unit': 'per GB-month'
            },
            {
                'id': 'msk_serverless',
                'name': 'MSK Serverless',
                'description': 'Serverless Kafka',
                'price_per_partition_hour': 0.0015,
                'price_per_gb_ingress': 0.10,
                'unit': 'per partition-hour + GB ingress'
            }
        ]
    },
    
    'data_pipeline': {
        'name': 'Data Pipeline',
        'low_level_services': [
            {
                'id': 'pipeline',
                'name': 'Pipeline',
                'description': 'Data workflow',
                'price_per_pipeline_month': 1.00,
                'unit': 'per active pipeline-month'
            },
            {
                'id': 'pipeline_activity',
                'name': 'Pipeline Activity',
                'description': 'Data transformation',
                'price_per_activity': 0.60,
                'unit': 'per EC2 instance-hour'
            }
        ]
    },
    
    # ========== MESSAGING ==========
    'sqs': {
        'name': 'Simple Queue Service',
        'low_level_services': [
            {
                'id': 'sqs_standard_request',
                'name': 'Standard Queue Request',
                'description': 'Message operations',
                'price_per_million': 0.40,
                'unit': 'per million requests'
            },
            {
                'id': 'sqs_fifo_request',
                'name': 'FIFO Queue Request',
                'description': 'FIFO message operations',
                'price_per_million': 0.50,
                'unit': 'per million requests'
            },
            {
                'id': 'sqs_data_transfer',
                'name': 'Data Transfer',
                'description': 'Message content',
                'price_per_gb': 0.00,
                'unit': '64KB chunked into requests'
            },
            {
                'id': 'sqs_kms_encryption',
                'name': 'KMS Encryption',
                'description': 'Server-side encryption',
                'price_per_million': 0.024,
                'unit': 'per million KMS requests'
            }
        ]
    },
    
    'sns': {
        'name': 'Simple Notification Service',
        'low_level_services': [
            {
                'id': 'sns_publish',
                'name': 'Publish Request',
                'description': 'Message publication',
                'price_per_million': 0.50,
                'unit': 'per million requests'
            },
            {
                'id': 'sns_http_delivery',
                'name': 'HTTP/S Delivery',
                'description': 'Webhook notifications',
                'price_per_million': 0.60,
                'unit': 'per million deliveries'
            },
            {
                'id': 'sns_email_delivery',
                'name': 'Email Delivery',
                'description': 'Email notifications',
                'price_per_million': 2.00,
                'unit': 'per million deliveries'
            },
            {
                'id': 'sns_email_json_delivery',
                'name': 'Email-JSON Delivery',
                'description': 'JSON email notifications',
                'price_per_million': 2.00,
                'unit': 'per million deliveries'
            },
            {
                'id': 'sns_sms_us',
                'name': 'SMS (US)',
                'description': 'US text messages',
                'price_per_sms': 0.00645,
                'unit': 'per SMS'
            },
            {
                'id': 'sns_sms_global',
                'name': 'SMS (Global)',
                'description': 'International SMS',
                'price_per_sms': 0.00645,
                'unit': 'varies by country'
            },
            {
                'id': 'sns_mobile_push',
                'name': 'Mobile Push',
                'description': 'App notifications',
                'price_per_million': 0.50,
                'unit': 'per million deliveries'
            },
            {
                'id': 'sns_topic',
                'name': 'Topic',
                'description': 'Message channel',
                'price_per_million': 0.50,
                'unit': 'per million publishes'
            }
        ]
    },
    
    'eventbridge': {
        'name': 'EventBridge',
        'low_level_services': [
            {
                'id': 'eventbridge_custom_event',
                'name': 'Custom Event',
                'description': 'Custom events',
                'price_per_million': 1.00,
                'unit': 'per million events'
            },
            {
                'id': 'eventbridge_schema_registry',
                'name': 'Schema Registry',
                'description': 'Event schemas',
                'price_per_registry_month': 0.40,
                'unit': 'per registry-month'
            },
            {
                'id': 'eventbridge_schema_discovery',
                'name': 'Schema Discovery',
                'description': 'Automatic schema creation',
                'price_per_million': 1.00,
                'unit': 'per million events'
            },
            {
                'id': 'eventbridge_api_destination',
                'name': 'API Destination',
                'description': 'HTTP endpoints',
                'price_per_invocation': 0.001,
                'unit': 'per invocation'
            },
            {
                'id': 'eventbridge_connection',
                'name': 'Connection',
                'description': 'External source auth',
                'price_per_connection_month': 0.10,
                'unit': 'per connection-month'
            },
            {
                'id': 'eventbridge_archive',
                'name': 'Archive',
                'description': 'Event storage',
                'price_per_gb_month': 0.02,
                'unit': 'per GB-month'
            },
            {
                'id': 'eventbridge_replay',
                'name': 'Replay',
                'description': 'Event replay',
                'price_per_replay': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'mq': {
        'name': 'Amazon MQ',
        'low_level_services': [
            {
                'id': 'mq_broker',
                'name': 'Broker Instance',
                'description': 'ActiveMQ/RabbitMQ broker',
                'price_per_hour': 0.15,
                'unit': 'per broker-hour (varies by type)'
            },
            {
                'id': 'mq_storage',
                'name': 'Broker Storage',
                'description': 'Message storage',
                'price_per_gb_month': 0.10,
                'unit': 'per GB-month'
            }
        ]
    },
    
    # ========== APPLICATION INTEGRATION ==========
    'stepfunctions': {
        'name': 'Step Functions',
        'low_level_services': [
            {
                'id': 'stepfunctions_standard',
                'name': 'Standard Workflow',
                'description': 'Long-running workflows',
                'price_per_million_transitions': 25.00,
                'unit': 'per million state transitions'
            },
            {
                'id': 'stepfunctions_express',
                'name': 'Express Workflow',
                'description': 'High-volume workflows',
                'price_per_million_requests': 1.00,
                'price_per_gb': 0.10,
                'unit': 'per million requests + GB'
            },
            {
                'id': 'stepfunctions_activity',
                'name': 'Activity',
                'description': 'External task integration',
                'price_per_million': 25.00,
                'unit': 'per million state transitions'
            }
        ]
    },
    
    'appsync': {
        'name': 'AppSync',
        'low_level_services': [
            {
                'id': 'appsync_query',
                'name': 'Query/Modification',
                'description': 'GraphQL operations',
                'price_per_million': 4.00,
                'unit': 'per million requests'
            },
            {
                'id': 'appsync_realtime',
                'name': 'Real-time Subscriptions',
                'description': 'WebSocket connections',
                'price_per_million': 2.00,
                'price_per_connection_hour': 0.08,
                'unit': 'per million messages + connection-hour'
            },
            {
                'id': 'appsync_cache',
                'name': 'Caching',
                'description': 'Response caching',
                'price_per_gb_hour': 0.02,
                'unit': 'per GB-hour'
            }
        ]
    },
    
    # ========== DEPLOYMENT & MANAGEMENT ==========
    'cloudformation': {
        'name': 'CloudFormation',
        'low_level_services': [
            {
                'id': 'cfn_stack',
                'name': 'Stack',
                'description': 'Resource collection',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'cfn_stackset',
                'name': 'StackSet',
                'description': 'Multi-account stacks',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'cfn_change_set',
                'name': 'Change Set',
                'description': 'Change preview',
                'price_per_set': 0.00,
                'unit': 'free'
            },
            {
                'id': 'cfn_macro',
                'name': 'Macro',
                'description': 'Template processing',
                'price_per_hour': 0.00,
                'unit': 'Lambda billing applies'
            },
            {
                'id': 'cfn_custom_resource',
                'name': 'Custom Resource',
                'description': 'External resources',
                'price_per_hour': 0.00,
                'unit': 'Lambda billing applies'
            },
            {
                'id': 'cfn_registry',
                'name': 'Registry',
                'description': 'Resource provider registry',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'cfn_private_registry',
                'name': 'Private Registry',
                'description': 'Private extensions',
                'price_per_hour': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'cloudtrail': {
        'name': 'CloudTrail',
        'low_level_services': [
            {
                'id': 'cloudtrail_management',
                'name': 'Management Events',
                'description': 'Control plane audit',
                'price_per_100k': 2.00,
                'unit': 'per 100,000 events'
            },
            {
                'id': 'cloudtrail_data',
                'name': 'Data Events',
                'description': 'Data plane audit',
                'price_per_100k': 0.10,
                'unit': 'per 100,000 events'
            },
            {
                'id': 'cloudtrail_insights',
                'name': 'Insights Events',
                'description': 'Anomaly detection',
                'price_per_100k': 0.35,
                'unit': 'per 100,000 events'
            },
            {
                'id': 'cloudtrail_lake',
                'name': 'CloudTrail Lake',
                'description': 'Managed audit logs',
                'price_per_gb_ingested': 2.50,
                'price_per_gb_scanned': 0.00765,
                'unit': 'per GB ingested + scanned'
            }
        ]
    },
    
    'config': {
        'name': 'Config',
        'low_level_services': [
            {
                'id': 'config_item',
                'name': 'Configuration Item',
                'description': 'Resource snapshot',
                'price_per_item': 0.003,
                'unit': 'per configuration item'
            },
            {
                'id': 'config_rule',
                'name': 'Config Rule',
                'description': 'Compliance evaluation',
                'price_per_rule_evaluation': 0.001,
                'unit': 'per rule evaluation'
            },
            {
                'id': 'config_conformance_pack',
                'name': 'Conformance Pack',
                'description': 'Rule collections',
                'price_per_evaluation': 0.001,
                'unit': 'per rule evaluation'
            },
            {
                'id': 'config_advanced_query',
                'name': 'Advanced Query',
                'description': 'Resource query',
                'price_per_query': 0.003,
                'unit': 'per query'
            }
        ]
    },
    
    'ops_works': {
        'name': 'OpsWorks',
        'low_level_services': [
            {
                'id': 'opsworks_automation',
                'name': 'OpsWorks Automation',
                'description': 'Chef automation',
                'price_per_hour': 0.015,
                'unit': 'per instance-hour'
            },
            {
                'id': 'opsworks_stacks',
                'name': 'OpsWorks Stacks',
                'description': 'Legacy Chef',
                'price_per_hour': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'system_manager': {
        'name': 'Systems Manager',
        'low_level_services': [
            {
                'id': 'ssm_on_prem_instance',
                'name': 'On-Premises Instance',
                'description': 'Hybrid management',
                'price_per_instance_hour': 0.008,
                'unit': 'per instance-hour'
            },
            {
                'id': 'ssm_parameter_standard',
                'name': 'Standard Parameter',
                'description': 'Configuration storage',
                'price_per_parameter': 0.00,
                'unit': 'free'
            },
            {
                'id': 'ssm_parameter_advanced',
                'name': 'Advanced Parameter',
                'description': 'Premium configuration',
                'price_per_parameter_month': 0.05,
                'unit': 'per parameter-month'
            },
            {
                'id': 'ssm_automation',
                'name': 'Automation',
                'description': 'Workflow automation',
                'price_per_instance_hour': 0.008,
                'unit': 'per instance-hour (on-prem)'
            },
            {
                'id': 'ssm_patch',
                'name': 'Patch Manager',
                'description': 'OS patching',
                'price_per_instance_hour': 0.008,
                'unit': 'per instance-hour (on-prem)'
            },
            {
                'id': 'ssm_inventory',
                'name': 'Inventory',
                'description': 'Resource inventory',
                'price_per_instance_hour': 0.008,
                'unit': 'per instance-hour (on-prem)'
            },
            {
                'id': 'ssm_session',
                'name': 'Session Manager',
                'description': 'Secure shell',
                'price_per_session': 0.00,
                'unit': 'data transfer billed'
            },
            {
                'id': 'ssm_incident_manager',
                'name': 'Incident Manager',
                'description': 'Incident response',
                'price_per_contact_month': 0.125,
                'price_per_incident': 9.00,
                'unit': 'per contact-month + per incident'
            }
        ]
    },
    
    'trusted_advisor': {
        'name': 'Trusted Advisor',
        'low_level_services': [
            {
                'id': 'trusted_advisor_checks',
                'name': 'Core Checks',
                'description': 'Basic recommendations',
                'price_per_check': 0.00,
                'unit': 'free'
            },
            {
                'id': 'trusted_advisor_full',
                'name': 'Full Checks',
                'description': 'Premium recommendations',
                'price_per_month': 0.00,
                'unit': 'included in Business/Enterprise support'
            }
        ]
    },
    
    'well_architected': {
        'name': 'Well-Architected',
        'low_level_services': [
            {
                'id': 'wa_workload',
                'name': 'Workload',
                'description': 'Architecture review',
                'price_per_workload': 0.00,
                'unit': 'free'
            },
            {
                'id': 'wa_lens',
                'name': 'Custom Lens',
                'description': 'Custom review questions',
                'price_per_lens': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'cloud9': {
        'name': 'Cloud9',
        'low_level_services': [
            {
                'id': 'cloud9_ide',
                'name': 'Cloud9 IDE',
                'description': 'Cloud IDE',
                'price_per_hour': 0.00,
                'unit': 'EC2 pricing applies'
            },
            {
                'id': 'cloud9_ec2',
                'name': 'Cloud9 EC2',
                'description': 'Development environment',
                'price_per_hour': 0.00,
                'unit': 'EC2 instance pricing'
            }
        ]
    },
    
    'codestar': {
        'name': 'CodeStar',
        'low_level_services': [
            {
                'id': 'codestar_project',
                'name': 'CodeStar Project',
                'description': 'Development project',
                'price_per_hour': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'codeartifact': {
        'name': 'CodeArtifact',
        'low_level_services': [
            {
                'id': 'codeartifact_storage',
                'name': 'Storage',
                'description': 'Package storage',
                'price_per_gb_month': 0.05,
                'unit': 'per GB-month'
            },
            {
                'id': 'codeartifact_request',
                'name': 'Request',
                'description': 'Package operations',
                'price_per_10k': 0.005,
                'unit': 'per 10,000 requests'
            }
        ]
    },
    
    # ========== SECURITY, IDENTITY & COMPLIANCE ==========
    'iam': {
        'name': 'Identity & Access Management',
        'low_level_services': [
            {
                'id': 'iam_user',
                'name': 'User',
                'description': 'Individual identity',
                'price_per_user': 0.00,
                'unit': 'free'
            },
            {
                'id': 'iam_role',
                'name': 'Role',
                'description': 'Temporary credentials',
                'price_per_role': 0.00,
                'unit': 'free'
            },
            {
                'id': 'iam_group',
                'name': 'Group',
                'description': 'User collections',
                'price_per_group': 0.00,
                'unit': 'free'
            },
            {
                'id': 'iam_policy',
                'name': 'Policy',
                'description': 'Permission document',
                'price_per_policy': 0.00,
                'unit': 'free'
            },
            {
                'id': 'iam_analyzer',
                'name': 'Access Analyzer',
                'description': 'Resource exposure analysis',
                'price_per_analyzer_month': 1.00,
                'unit': 'per analyzer-month'
            },
            {
                'id': 'iam_saml',
                'name': 'SAML Provider',
                'description': 'SAML integration',
                'price_per_provider': 0.00,
                'unit': 'free'
            },
            {
                'id': 'iam_oidc',
                'name': 'OIDC Provider',
                'description': 'OpenID Connect integration',
                'price_per_provider': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'cognito': {
        'name': 'Cognito',
        'low_level_services': [
            {
                'id': 'cognito_mau',
                'name': 'Monthly Active Users',
                'description': 'User directory',
                'price_per_mau': 0.0055,
                'unit': 'per MAU (first 50k free)'
            },
            {
                'id': 'cognito_advanced_security',
                'name': 'Advanced Security',
                'description': 'Risk detection',
                'price_per_mau': 0.05,
                'unit': 'per 1k MAU'
            },
            {
                'id': 'cognito_mfa_sms',
                'name': 'SMS MFA',
                'description': 'Text message 2FA',
                'price_per_sms': 0.05,
                'unit': 'per SMS'
            },
            {
                'id': 'cognito_mfa_totp',
                'name': 'TOTP MFA',
                'description': 'Authenticator app',
                'price_per_usage': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'directory_service': {
        'name': 'Directory Service',
        'low_level_services': [
            {
                'id': 'ds_simple_ad',
                'name': 'Simple AD',
                'description': 'Basic directory',
                'price_per_hour': 0.05,
                'unit': 'per hour'
            },
            {
                'id': 'ds_microsoft_ad',
                'name': 'Managed Microsoft AD',
                'description': 'Active Directory',
                'price_per_hour': 0.166,
                'unit': 'per hour'
            },
            {
                'id': 'ds_ad_connector',
                'name': 'AD Connector',
                'description': 'On-prem proxy',
                'price_per_hour': 0.05,
                'unit': 'per hour'
            },
            {
                'id': 'ds_snapshot',
                'name': 'Directory Snapshot',
                'description': 'Directory backup',
                'price_per_gb_month': 0.095,
                'unit': 'per GB-month'
            }
        ]
    },
    
    'kms': {
        'name': 'Key Management Service',
        'low_level_services': [
            {
                'id': 'kms_cmk',
                'name': 'Customer Master Key',
                'description': 'Encryption key',
                'price_per_key_month': 1.00,
                'unit': 'per key-month'
            },
            {
                'id': 'kms_cmk_imported',
                'name': 'Imported Key',
                'description': 'External key material',
                'price_per_key_month': 1.00,
                'unit': 'per key-month'
            },
            {
                'id': 'kms_request',
                'name': 'API Request',
                'description': 'Encryption operations',
                'price_per_10k': 0.03,
                'unit': 'per 10,000 requests'
            },
            {
                'id': 'kms_hsm',
                'name': 'Custom Key Store',
                'description': 'CloudHSM-backed',
                'price_per_key_month': 1.00,
                'unit': 'per key-month + CloudHSM'
            },
            {
                'id': 'kms_rotation',
                'name': 'Automatic Rotation',
                'description': 'Key rotation',
                'price_per_key': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'cloudhsm': {
        'name': 'CloudHSM',
        'low_level_services': [
            {
                'id': 'cloudhsm_cluster',
                'name': 'CloudHSM Cluster',
                'description': 'HSM cluster management',
                'price_per_hsm_hour': 1.46,
                'unit': 'per HSM-hour'
            },
            {
                'id': 'cloudhsm_backup',
                'name': 'HSM Backup',
                'description': 'HSM configuration backup',
                'price_per_gb_month': 0.025,
                'unit': 'per GB-month'
            }
        ]
    },
    
    'waf': {
        'name': 'Web Application Firewall',
        'low_level_services': [
            {
                'id': 'waf_acl',
                'name': 'Web ACL',
                'description': 'Rule collection',
                'price_per_month': 5.00,
                'unit': 'per web ACL-month'
            },
            {
                'id': 'waf_rule',
                'name': 'Rule',
                'description': 'Inspection rule',
                'price_per_month': 1.00,
                'unit': 'per rule-month'
            },
            {
                'id': 'waf_rule_group',
                'name': 'Rule Group',
                'description': 'Bundle of rules',
                'price_per_month': 1.00,
                'unit': 'per rule-month'
            },
            {
                'id': 'waf_ip_set',
                'name': 'IP Set',
                'description': 'IP address list',
                'price_per_set_month': 1.00,
                'unit': 'per set-month'
            },
            {
                'id': 'waf_regex_set',
                'name': 'Regex Pattern Set',
                'description': 'Pattern matching',
                'price_per_set_month': 1.00,
                'unit': 'per set-month'
            },
            {
                'id': 'waf_rate_rule',
                'name': 'Rate-based Rule',
                'description': 'Rate limiting',
                'price_per_month': 1.00,
                'unit': 'per rule-month'
            },
            {
                'id': 'waf_logging',
                'name': 'Logging',
                'description': 'Traffic logs',
                'price_per_gb': 1.00,
                'unit': 'per GB processed'
            },
            {
                'id': 'waf_captcha',
                'name': 'CAPTCHA',
                'description': 'Bot challenge',
                'price_per_thousand': 0.40,
                'unit': 'per 1,000 requests'
            },
            {
                'id': 'waf_bot_control',
                'name': 'Bot Control',
                'description': 'Bot mitigation',
                'price_per_month': 10.00,
                'unit': 'per ACL-month'
            }
        ]
    },
    
    'shield': {
        'name': 'Shield',
        'low_level_services': [
            {
                'id': 'shield_standard',
                'name': 'Shield Standard',
                'description': 'Basic DDoS protection',
                'price_per_month': 0.00,
                'unit': 'free'
            },
            {
                'id': 'shield_advanced',
                'name': 'Shield Advanced',
                'description': 'Enhanced DDoS',
                'price_per_month': 3000.00,
                'unit': 'per month'
            }
        ]
    },
    
    'guardduty': {
        'name': 'GuardDuty',
        'low_level_services': [
            {
                'id': 'guardduty_ec2',
                'name': 'EC2 Event Analysis',
                'description': 'EC2 threat detection',
                'price_per_million': 2.00,
                'unit': 'per million events'
            },
            {
                'id': 'guardduty_s3',
                'name': 'S3 Event Analysis',
                'description': 'S3 threat detection',
                'price_per_million': 0.20,
                'unit': 'per million events'
            },
            {
                'id': 'guardduty_k8s',
                'name': 'Kubernetes Audit',
                'description': 'EKS threat detection',
                'price_per_million': 0.20,
                'unit': 'per million events'
            },
            {
                'id': 'guardduty_malware',
                'name': 'Malware Protection',
                'description': 'Malware scanning',
                'price_per_gb': 0.15,
                'unit': 'per GB scanned'
            }
        ]
    },
    
    'inspector': {
        'name': 'Inspector',
        'low_level_services': [
            {
                'id': 'inspector_ec2',
                'name': 'EC2 Assessment',
                'description': 'EC2 vulnerability scanning',
                'price_per_instance_month': 0.15,
                'unit': 'per instance-month'
            },
            {
                'id': 'inspector_ecr',
                'name': 'ECR Assessment',
                'description': 'Container image scanning',
                'price_per_image': 0.10,
                'unit': 'per image'
            },
            {
                'id': 'inspector_lambda',
                'name': 'Lambda Assessment',
                'description': 'Function vulnerability',
                'price_per_function_month': 0.09,
                'unit': 'per function-month'
            }
        ]
    },
    
    'macie': {
        'name': 'Macie',
        'low_level_services': [
            {
                'id': 'macie_s3_classification',
                'name': 'S3 Classification',
                'description': 'Sensitive data discovery',
                'price_per_gb': 0.10,
                'unit': 'per GB (first 1GB free)'
            },
            {
                'id': 'macie_job',
                'name': 'Sensitive Data Job',
                'description': 'Scan job',
                'price_per_gb': 0.10,
                'unit': 'per GB scanned'
            },
            {
                'id': 'macie_custom_identifier',
                'name': 'Custom Identifier',
                'description': 'Custom PII patterns',
                'price_per_identifier_month': 1.00,
                'unit': 'per identifier-month'
            }
        ]
    },
    
    'security_hub': {
        'name': 'Security Hub',
        'low_level_services': [
            {
                'id': 'security_hub_finding',
                'name': 'Security Finding',
                'description': 'Compliance findings',
                'price_per_100k': 0.30,
                'unit': 'per 100,000 findings'
            },
            {
                'id': 'security_hub_config_rule',
                'name': 'Security Standard',
                'description': 'Compliance checks',
                'price_per_check': 0.001,
                'unit': 'per security check'
            }
        ]
    },
    
    'artifact': {
        'name': 'Artifact',
        'low_level_services': [
            {
                'id': 'artifact_report',
                'name': 'Compliance Report',
                'description': 'Audit/compliance reports',
                'price_per_report': 0.00,
                'unit': 'free'
            },
            {
                'id': 'artifact_agreement',
                'name': 'Business Agreement',
                'description': 'Legal agreements',
                'price_per_agreement': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    # ========== MIGRATION & TRANSFER ==========
    'dms': {
        'name': 'Database Migration Service',
        'low_level_services': [
            {
                'id': 'dms_replication_instance_small',
                'name': 'Replication Instance (Small)',
                'description': 'Database migration compute',
                'price_per_hour': 0.115,
                'unit': 'per hour'
            },
            {
                'id': 'dms_replication_instance_medium',
                'name': 'Replication Instance (Medium)',
                'description': 'Database migration compute',
                'price_per_hour': 0.235,
                'unit': 'per hour'
            },
            {
                'id': 'dms_replication_instance_large',
                'name': 'Replication Instance (Large)',
                'description': 'Database migration compute',
                'price_per_hour': 0.470,
                'unit': 'per hour'
            },
            {
                'id': 'dms_replication_instance_xlarge',
                'name': 'Replication Instance (XLarge)',
                'description': 'Database migration compute',
                'price_per_hour': 0.940,
                'unit': 'per hour'
            },
            {
                'id': 'dms_premium_support',
                'name': 'Premium Support',
                'description': 'AWS migration assistance',
                'price_per_hour': 1.00,
                'unit': 'per hour'
            }
        ]
    },
    
    'datasync': {
        'name': 'DataSync',
        'low_level_services': [
            {
                'id': 'datasync_agent',
                'name': 'DataSync Agent',
                'description': 'On-prem data transfer',
                'price_per_hour': 0.00,
                'unit': 'free'
            },
            {
                'id': 'datasync_task',
                'name': 'DataSync Task',
                'description': 'Data transfer job',
                'price_per_gb': 0.0125,
                'unit': 'per GB transferred'
            }
        ]
    },
    
    'transfer_family': {
        'name': 'Transfer Family',
        'low_level_services': [
            {
                'id': 'transfer_server',
                'name': 'SFTP/FTPS/FTP Server',
                'description': 'Managed file transfer',
                'price_per_hour': 0.30,
                'unit': 'per server-hour'
            },
            {
                'id': 'transfer_data',
                'name': 'Data Transfer',
                'description': 'File upload/download',
                'price_per_gb': 0.04,
                'unit': 'per GB transferred'
            }
        ]
    },
    
    'snowball': {
        'name': 'Snowball',
        'low_level_services': [
            {
                'id': 'snowball_edge_device',
                'name': 'Snowball Edge',
                'description': 'Petabyte-scale transport',
                'price_per_device': 300.00,
                'price_per_day': 30.00,
                'unit': 'per device + per day'
            },
            {
                'id': 'snowball_compute',
                'name': 'Snowball Compute',
                'description': 'Edge computing',
                'price_per_hour': 0.50,
                'unit': 'per hour'
            }
        ]
    },
    
    # ========== MACHINE LEARNING ==========
    'sagemaker': {
        'name': 'SageMaker',
        'low_level_services': [
            {
                'id': 'sagemaker_notebook',
                'name': 'Notebook Instance',
                'description': 'Jupyter notebook',
                'price_per_hour': 0.05,
                'unit': 'per hour (varies by type)'
            },
            {
                'id': 'sagemaker_training',
                'name': 'Training Job',
                'description': 'Model training',
                'price_per_hour': 0.05,
                'unit': 'per hour (varies by type)'
            },
            {
                'id': 'sagemaker_inference',
                'name': 'Inference Endpoint',
                'description': 'Real-time predictions',
                'price_per_hour': 0.05,
                'unit': 'per hour (varies by type)'
            },
            {
                'id': 'sagemaker_serverless',
                'name': 'Serverless Inference',
                'description': 'On-demand predictions',
                'price_per_gb_second': 0.0000333,
                'price_per_million': 0.30,
                'unit': 'per GB-second + per million requests'
            },
            {
                'id': 'sagemaker_data_wrangler',
                'name': 'Data Wrangler',
                'description': 'Data preparation',
                'price_per_hour': 0.49,
                'unit': 'per hour'
            },
            {
                'id': 'sagemaker_feature_store',
                'name': 'Feature Store',
                'description': 'ML feature management',
                'price_per_gb_month': 0.20,
                'unit': 'per GB-month'
            },
            {
                'id': 'sagemaker_pipeline',
                'name': 'Pipeline',
                'description': 'ML workflows',
                'price_per_run': 0.00,
                'unit': 'resource pricing applies'
            }
        ]
    },
    
    'comprehend': {
        'name': 'Comprehend',
        'low_level_services': [
            {
                'id': 'comprehend_entity',
                'name': 'Entity Detection',
                'description': 'Named entity recognition',
                'price_per_million_units': 0.10,
                'unit': 'per 100 units'
            },
            {
                'id': 'comprehend_keyphrase',
                'name': 'Key Phrase Extraction',
                'description': 'Key phrase detection',
                'price_per_million_units': 0.10,
                'unit': 'per 100 units'
            },
            {
                'id': 'comprehend_sentiment',
                'name': 'Sentiment Analysis',
                'description': 'Emotion detection',
                'price_per_million_units': 0.10,
                'unit': 'per 100 units'
            },
            {
                'id': 'comprehend_language',
                'name': 'Language Detection',
                'description': 'Language identification',
                'price_per_million_units': 0.10,
                'unit': 'per 100 units'
            },
            {
                'id': 'comprehend_custom',
                'name': 'Custom Model',
                'description': 'Custom entity/classification',
                'price_per_training_hour': 1.00,
                'price_per_inference_unit': 0.0005,
                'unit': 'per training hour + inference unit'
            }
        ]
    },
    
    'rekognition': {
        'name': 'Rekognition',
        'low_level_services': [
            {
                'id': 'rekognition_image',
                'name': 'Image Analysis',
                'description': 'Object/face detection',
                'price_per_thousand': 1.00,
                'unit': 'per 1,000 images'
            },
            {
                'id': 'rekognition_video',
                'name': 'Video Analysis',
                'description': 'Video content analysis',
                'price_per_minute': 0.12,
                'unit': 'per minute'
            },
            {
                'id': 'rekognition_face_storage',
                'name': 'Face Storage',
                'description': 'Face metadata',
                'price_per_thousand': 0.01,
                'unit': 'per 1,000 faces-month'
            }
        ]
    },
    
    'textract': {
        'name': 'Textract',
        'low_level_services': [
            {
                'id': 'textract_page',
                'name': 'Document Analysis',
                'description': 'Text extraction',
                'price_per_page': 0.0015,
                'unit': 'per page'
            },
            {
                'id': 'textract_form',
                'name': 'Form Analysis',
                'description': 'Form data extraction',
                'price_per_page': 0.015,
                'unit': 'per page'
            },
            {
                'id': 'textract_table',
                'name': 'Table Analysis',
                'description': 'Table extraction',
                'price_per_page': 0.015,
                'unit': 'per page'
            },
            {
                'id': 'textract_query',
                'name': 'Query API',
                'description': 'Query-based extraction',
                'price_per_page': 0.0015,
                'unit': 'per page + query'
            }
        ]
    },
    
    'translate': {
        'name': 'Translate',
        'low_level_services': [
            {
                'id': 'translate_text',
                'name': 'Text Translation',
                'description': 'Language translation',
                'price_per_million_char': 15.00,
                'unit': 'per million characters'
            },
            {
                'id': 'translate_custom',
                'name': 'Custom Terminology',
                'description': 'Custom vocabulary',
                'price_per_term': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    'transcribe': {
        'name': 'Transcribe',
        'low_level_services': [
            {
                'id': 'transcribe_streaming',
                'name': 'Streaming Transcription',
                'description': 'Real-time speech-to-text',
                'price_per_second': 0.0004,
                'unit': 'per second'
            },
            {
                'id': 'transcribe_batch',
                'name': 'Batch Transcription',
                'description': 'File-based transcription',
                'price_per_second': 0.0002,
                'unit': 'per second'
            }
        ]
    },
    
    'polly': {
        'name': 'Polly',
        'low_level_services': [
            {
                'id': 'polly_neural',
                'name': 'Neural TTS',
                'description': 'Neural voices',
                'price_per_million_char': 16.00,
                'unit': 'per million characters'
            },
            {
                'id': 'polly_standard',
                'name': 'Standard TTS',
                'description': 'Standard voices',
                'price_per_million_char': 4.00,
                'unit': 'per million characters'
            },
            {
                'id': 'polly_long_form',
                'name': 'Long Form TTS',
                'description': 'Podcast/audiobook',
                'price_per_hour': 100.00,
                'unit': 'per hour'
            }
        ]
    },
    
    'lex': {
        'name': 'Lex',
        'low_level_services': [
            {
                'id': 'lex_request',
                'name': 'Text Request',
                'description': 'Chatbot text processing',
                'price_per_thousand': 0.75,
                'unit': 'per 1,000 requests'
            },
            {
                'id': 'lex_voice',
                'name': 'Voice Request',
                'description': 'Speech processing',
                'price_per_thousand': 4.00,
                'unit': 'per 1,000 requests'
            }
        ]
    },
    
    'personalize': {
        'name': 'Personalize',
        'low_level_services': [
            {
                'id': 'personalize_training',
                'name': 'Model Training',
                'description': 'Recommendation training',
                'price_per_hour': 0.60,
                'unit': 'per training hour'
            },
            {
                'id': 'personalize_inference',
                'name': 'Real-time Inference',
                'description': 'Recommendation generation',
                'price_per_thousand': 0.20,
                'unit': 'per 1,000 requests'
            },
            {
                'id': 'personalize_data_ingestion',
                'name': 'Data Ingestion',
                'description': 'User/item data',
                'price_per_gb': 0.05,
                'unit': 'per GB'
            }
        ]
    },
    
    'forecast': {
        'name': 'Forecast',
        'low_level_services': [
            {
                'id': 'forecast_training',
                'name': 'Model Training',
                'description': 'Time-series training',
                'price_per_hour': 0.60,
                'unit': 'per training hour'
            },
            {
                'id': 'forecast_inference',
                'name': 'Forecast Generation',
                'description': 'Predictions',
                'price_per_thousand': 0.20,
                'unit': 'per 1,000 forecasts'
            }
        ]
    },
    
    'kendra': {
        'name': 'Kendra',
        'low_level_services': [
            {
                'id': 'kendra_index_developer',
                'name': 'Developer Edition',
                'description': 'Enterprise search',
                'price_per_hour': 0.60,
                'unit': 'per hour'
            },
            {
                'id': 'kendra_index_enterprise',
                'name': 'Enterprise Edition',
                'description': 'Advanced enterprise search',
                'price_per_hour': 1.20,
                'unit': 'per hour'
            },
            {
                'id': 'kendra_query',
                'name': 'Query',
                'description': 'Search queries',
                'price_per_thousand': 0.50,
                'unit': 'per 1,000 queries'
            },
            {
                'id': 'kendra_document',
                'name': 'Document',
                'description': 'Indexed documents',
                'price_per_thousand': 2.00,
                'unit': 'per 1,000 documents'
            }
        ]
    },
    
    'fraud_detector': {
        'name': 'Fraud Detector',
        'low_level_services': [
            {
                'id': 'fraud_training',
                'name': 'Model Training',
                'description': 'Fraud model training',
                'price_per_hour': 0.60,
                'unit': 'per training hour'
            },
            {
                'id': 'fraud_inference',
                'name': 'Fraud Prediction',
                'description': 'Real-time fraud detection',
                'price_per_thousand': 20.00,
                'unit': 'per 1,000 predictions'
            }
        ]
    },
    
    'lookout_vision': {
        'name': 'Lookout for Vision',
        'low_level_services': [
            {
                'id': 'lookout_training',
                'name': 'Model Training',
                'description': 'Anomaly detection training',
                'price_per_hour': 1.00,
                'unit': 'per training hour'
            },
            {
                'id': 'lookout_inference',
                'name': 'Anomaly Detection',
                'description': 'Image anomaly detection',
                'price_per_image': 0.008,
                'unit': 'per image'
            }
        ]
    },
    
    'monitron': {
        'name': 'Monitron',
        'low_level_services': [
            {
                'id': 'monitron_sensor',
                'name': 'Sensor',
                'description': 'Industrial sensor',
                'price_per_sensor_year': 36.00,
                'unit': 'per sensor-year'
            },
            {
                'id': 'monitron_gateway',
                'name': 'Gateway',
                'description': 'Sensor gateway',
                'price_per_gateway_year': 120.00,
                'unit': 'per gateway-year'
            }
        ]
    },
    
    # ========== END USER COMPUTING ==========
    'workspaces': {
        'name': 'WorkSpaces',
        'low_level_services': [
            {
                'id': 'workspace_value',
                'name': 'Value Bundle',
                'description': '1 vCPU, 2GB RAM',
                'price_per_month': 7.25,
                'price_per_hour': 0.10,
                'unit': 'per month (AlwaysOn) or hour (AutoStop)'
            },
            {
                'id': 'workspace_standard',
                'name': 'Standard Bundle',
                'description': '2 vCPU, 4GB RAM',
                'price_per_month': 12.00,
                'price_per_hour': 0.15,
                'unit': 'per month (AlwaysOn) or hour (AutoStop)'
            },
            {
                'id': 'workspace_performance',
                'name': 'Performance Bundle',
                'description': '2 vCPU, 8GB RAM',
                'price_per_month': 20.00,
                'price_per_hour': 0.25,
                'unit': 'per month (AlwaysOn) or hour (AutoStop)'
            },
            {
                'id': 'workspace_power',
                'name': 'Power Bundle',
                'description': '4 vCPU, 16GB RAM',
                'price_per_month': 40.00,
                'price_per_hour': 0.50,
                'unit': 'per month (AlwaysOn) or hour (AutoStop)'
            },
            {
                'id': 'workspace_root_volume',
                'name': 'Root Volume',
                'description': 'System storage',
                'price_per_gb_month': 0.00,
                'unit': 'included in bundle'
            },
            {
                'id': 'workspace_user_volume',
                'name': 'User Volume',
                'description': 'Persistent storage',
                'price_per_gb_month': 3.00,
                'unit': 'per 100GB-month'
            }
        ]
    },
    
    'appstream': {
        'name': 'AppStream 2.0',
        'low_level_services': [
            {
                'id': 'appstream_streaming',
                'name': 'Streaming Instance',
                'description': 'Application streaming',
                'price_per_hour': 0.15,
                'unit': 'per hour (varies by instance)'
            },
            {
                'id': 'appstream_user',
                'name': 'User',
                'description': 'Active user',
                'price_per_month': 4.19,
                'unit': 'per user-month'
            },
            {
                'id': 'appstream_image_builder',
                'name': 'Image Builder',
                'description': 'Application packaging',
                'price_per_hour': 0.15,
                'unit': 'per hour'
            }
        ]
    },
    
    'worklink': {
        'name': 'WorkLink',
        'low_level_services': [
            {
                'id': 'worklink_user',
                'name': 'User',
                'description': 'Secure intranet access',
                'price_per_month': 5.00,
                'unit': 'per user-month'
            },
            {
                'id': 'worklink_data',
                'name': 'Data Transfer',
                'description': 'Intranet content',
                'price_per_gb': 0.15,
                'unit': 'per GB'
            }
        ]
    },
    
    # ========== IOT ==========
    'iot_core': {
        'name': 'IoT Core',
        'low_level_services': [
            {
                'id': 'iot_connect',
                'name': 'Device Connection',
                'description': 'MQTT/HTTPS connection',
                'price_per_million_minutes': 0.80,
                'unit': 'per million minutes'
            },
            {
                'id': 'iot_message',
                'name': 'Message',
                'description': 'Device telemetry',
                'price_per_million': 1.00,
                'unit': 'per million messages'
            },
            {
                'id': 'iot_rule',
                'name': 'Rules Engine',
                'description': 'Message transformation',
                'price_per_million_actions': 0.15,
                'unit': 'per million rule actions'
            },
            {
                'id': 'iot_device_shadow',
                'name': 'Device Shadow',
                'description': 'Device state',
                'price_per_million': 1.25,
                'unit': 'per million operations'
            }
        ]
    },
    
    'iot_analytics': {
        'name': 'IoT Analytics',
        'low_level_services': [
            {
                'id': 'iot_analytics_ingestion',
                'name': 'Message Ingestion',
                'description': 'IoT data ingestion',
                'price_per_mb': 0.20,
                'unit': 'per MB'
            },
            {
                'id': 'iot_analytics_storage',
                'name': 'Data Storage',
                'description': 'IoT data lake',
                'price_per_gb_month': 0.023,
                'unit': 'per GB-month'
            },
            {
                'id': 'iot_analytics_execution',
                'name': 'Pipeline Execution',
                'description': 'Data processing',
                'price_per_hour': 0.36,
                'unit': 'per hour'
            }
        ]
    },
    
    'iot_sitewise': {
        'name': 'IoT SiteWise',
        'low_level_services': [
            {
                'id': 'sitewise_data_ingestion',
                'name': 'Data Ingestion',
                'description': 'Industrial data',
                'price_per_mb': 0.10,
                'unit': 'per MB'
            },
            {
                'id': 'sitewise_data_storage',
                'name': 'Data Storage',
                'description': 'Industrial data lake',
                'price_per_gb_month': 0.023,
                'unit': 'per GB-month'
            },
            {
                'id': 'sitewise_compute',
                'name': 'Compute',
                'description': 'Edge processing',
                'price_per_hour': 0.50,
                'unit': 'per hour'
            }
        ]
    },
    
    'iot_events': {
        'name': 'IoT Events',
        'low_level_services': [
            {
                'id': 'iot_events_message',
                'name': 'Message',
                'description': 'Event detection',
                'price_per_million': 1.05,
                'unit': 'per million messages'
            },
            {
                'id': 'iot_events_analysis',
                'name': 'Analysis',
                'description': 'Detector model execution',
                'price_per_hour': 0.50,
                'unit': 'per hour'
            }
        ]
    },
    
    'greengrass': {
        'name': 'Greengrass',
        'low_level_services': [
            {
                'id': 'greengrass_device',
                'name': 'Device',
                'description': 'Edge device',
                'price_per_device_month': 0.16,
                'unit': 'per device-month'
            },
            {
                'id': 'greengrass_connector',
                'name': 'Connector',
                'description': 'Service integration',
                'price_per_connector_month': 0.05,
                'unit': 'per connector-month'
            },
            {
                'id': 'greengrass_cloud_traffic',
                'name': 'Cloud Traffic',
                'description': 'Device-cloud data',
                'price_per_gb': 0.10,
                'unit': 'per GB'
            }
        ]
    },
    
    # ========== GAME DEVELOPMENT ==========
    'gamelift': {
        'name': 'GameLift',
        'low_level_services': [
            {
                'id': 'gamelift_instance',
                'name': 'Game Server Instance',
                'description': 'Multiplayer hosting',
                'price_per_hour': 0.023,
                'unit': 'per hour (varies by type)'
            },
            {
                'id': 'gamelift_flexmatch',
                'name': 'FlexMatch',
                'description': 'Player matchmaking',
                'price_per_thousand': 1.00,
                'unit': 'per 1,000 matches'
            },
            {
                'id': 'gamelift_realtime',
                'name': 'Realtime Servers',
                'description': 'Low-latency serverless',
                'price_per_hour': 0.0008,
                'unit': 'per CCU-hour'
            }
        ]
    },
    
    # ========== SATELLITE ==========
    'ground_station': {
        'name': 'Ground Station',
        'low_level_services': [
            {
                'id': 'ground_station_contact',
                'name': 'Satellite Contact',
                'description': 'Satellite communication',
                'price_per_minute': 2.50,
                'unit': 'per minute'
            },
            {
                'id': 'ground_station_data_ingress',
                'name': 'Data Ingress',
                'description': 'Satellite data',
                'price_per_gb': 0.00,
                'unit': 'free'
            }
        ]
    },
    
    # ========== QUANTUM COMPUTING ==========
    'braket': {
        'name': 'Braket',
        'low_level_services': [
            {
                'id': 'braket_simulator',
                'name': 'Quantum Simulator',
                'description': 'Quantum circuit simulation',
                'price_per_hour': 0.075,
                'unit': 'per hour'
            },
            {
                'id': 'braket_rigetti',
                'name': 'Rigetti QPU',
                'description': 'Rigetti quantum processor',
                'price_per_task': 0.30,
                'price_per_shot': 0.001,
                'unit': 'per task + per shot'
            },
            {
                'id': 'braket_ionq',
                'name': 'IonQ QPU',
                'description': 'IonQ quantum processor',
                'price_per_task': 0.30,
                'price_per_shot': 0.01,
                'unit': 'per task + per shot'
            }
        ]
    }
}

# ============================================================
# DISCOVERY FUNCTIONS FOR ALL SERVICES
# ============================================================

# Import all discovery functions from separate modules
# Since this file is now 5000+ lines, we'll break it into modules

from .Discovery.vpc_discovery import *
from .Discovery.ec2_discovery import *
from .Discovery.s3_discovery import *
from .Discovery.rds_discovery import *
from .Discovery.dynamodb_discovery import *
from .Discovery.lambda_discovery import *
from .Discovery.ecs_discovery import *
from .Discovery.eks_discovery import *
from .Discovery.route53_discovery import *
from .Discovery.cloudfront_discovery import *
""""
from .Discovery.apigateway_discovery import *
from .Discovery.elb_discovery import *
from .Discovery.cloudwatch_discovery import *
from .Discovery.kms_discovery import *
from .Discovery.sqs_discovery import *
"""

#from .Discovery.sns_discovery import *
#from .Discovery.eventbridge_discovery import *
#from .Discovery.stepfunctions_discovery import *
from .Discovery.waf_discovery import *
#from .Discovery.shield_discovery import *
#from .Discovery.guardduty_discovery import *
#from .Discovery.cloudtrail_discovery import *
#from .Discovery.cloudformation_discovery import *
#from .Discovery.ssm_discovery import *
#from .Discovery.dms_discovery import *


# ============================================================
# MAIN ORCHESTRATION FUNCTION
# ============================================================

def assume_role_for_account(account):
    """Assume role for AWS account using platform credentials"""
    try:
        sts = boto3.client('sts')
        creds = sts.assume_role(
            RoleArn=account.role_arn,
            RoleSessionName="LowLevelServiceTracker",
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

def discover_region_services(creds, region):
    """Discover all low-level services in a specific region"""
    services = []
    
    # Execute all region-based discovery functions
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [

            executor.submit(discover_vpc_services, creds, region),
            executor.submit(discover_ec2_services, creds, region),
            executor.submit(discover_s3_services, creds, region),
            executor.submit(discover_rds_services, creds, region),
            executor.submit(discover_dynamodb_services, creds, region),
            executor.submit(discover_lambda_services, creds, region),
            executor.submit(discover_ecs_services, creds, region),
            executor.submit(discover_eks_services, creds, region),
            executor.submit(discover_waf_services, creds, region),
          
          #   executor.submit(discover_apigateway_services, creds, region),
          #  executor.submit(discover_elb_services, creds, region),
           # executor.submit(discover_cloudwatch_services, creds, region),
           # executor.submit(discover_kms_services, creds, region),
           # executor.submit(discover_sqs_services, creds, region),
           # executor.submit(discover_sns_services, creds, region),
           # executor.submit(discover_eventbridge_services, creds, region),
           # executor.submit(discover_stepfunctions_services, creds, region),

         
         #   executor.submit(discover_guardduty_services, creds, region),
         #   executor.submit(discover_cloudtrail_services, creds, region),
         #   executor.submit(discover_cloudformation_services, creds, region),
         #   executor.submit(discover_ssm_services, creds, region),
         #   executor.submit(discover_dms_services, creds, region),
           
        ]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result:
                    services.extend(result)
            except Exception as e:
                print(f"Error in discovery thread: {e}")
    
    return services

def discover_global_services(creds):
    """Discover global AWS services"""
    services = []
    
    # Global services
    services.extend(discover_route53_services(creds))
    services.extend(discover_cloudfront_distributions(creds))
   # services.extend(discover_shield_services(creds))
    
    return services

def discover_low_level_services(account_id, use_cache=True):
    """Discover ALL low-level AWS services with pricing information"""
    try:
        # Try cache first
        if use_cache:
            cache_key = f"low_level_services_{account_id}"
            cached_data = ResourceCache.get_cached_resources(cache_key)
            if cached_data:
                print(f"📦 Using cached low-level services for account {account_id}")
                return cached_data
        
        account = AWSAccountConnection.objects.get(id=account_id)
        creds = assume_role_for_account(account)
        
        if not creds:
            return {
                'error': 'Failed to assume role',
                'services': [],
                'summary': {'total_services': 0, 'estimated_monthly_cost': 0},
                'pricing_reference': LOW_LEVEL_SERVICES
            }
        
        # Initialize results
        all_services = []
        
        # Regions to check (major regions)
        regions_to_check = [
            'us-east-1',
             # 'us-west-1', 'us-west-2',
            #'eu-west-1', 'eu-west-2', 'eu-central-1', 
            "eu-north-1"
            #'ap-northeast-1', 'ap-southeast-1', 'ap-southeast-2'
        ]
        
        # Discover services in each region (parallel)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            region_futures = {
                executor.submit(discover_region_services, creds, region): region
                for region in regions_to_check
            }
            
            for future in concurrent.futures.as_completed(region_futures):
                region = region_futures[future]
                try:
                    region_services = future.result()
                    if region_services:
                        all_services.extend(region_services)
                        print(f"✅ Discovered {len(region_services)} services in {region}")
                except Exception as e:
                    print(f"❌ Error discovering services in {region}: {e}")
        
        # Add global services
        all_services.extend(discover_global_services(creds))
        
        # Calculate summary
        total_monthly_cost = sum(service.get('estimated_monthly_cost', 0) for service in all_services)
        
        # Group by service category
        grouped_services = {}
        for service in all_services:
            service_id = service['service_id']
            service_info = None
            category_name = "Other"
            
            # Find service info from LOW_LEVEL_SERVICES
            for category_key, category in LOW_LEVEL_SERVICES.items():
                for low_service in category['low_level_services']:
                    if low_service['id'] == service_id:
                        service_info = low_service
                        category_name = category['name']
                        break
                if service_info:
                    break
            
            if service_id not in grouped_services:
                grouped_services[service_id] = {
                    'service_info': service_info,
                    'category': category_name,
                    'resources': [],
                    'total_count': 0,
                    'total_monthly_cost': 0
                }
            
            grouped_services[service_id]['resources'].append(service)
            grouped_services[service_id]['total_count'] += 1
            grouped_services[service_id]['total_monthly_cost'] += service.get('estimated_monthly_cost', 0)
        
        # Prepare final response
        result = {
            'services_by_category': grouped_services,
            'all_resources': all_services,
            'summary': {
                'total_services': len(all_services),
                'estimated_monthly_cost': round(total_monthly_cost, 2),
                'unique_service_types': len(grouped_services),
                'unique_services_discovered': len(set(s['service_id'] for s in all_services)),
                'regions_scanned': regions_to_check,
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            'pricing_reference': LOW_LEVEL_SERVICES
        }
        
        # Cache the results (1 hour TTL)
        ResourceCache.cache_resources(f"low_level_services_{account_id}", result)
        
        return result
        
    except AWSAccountConnection.DoesNotExist:
        return {
            'error': f"Account {account_id} not found",
            'services': [],
            'summary': {'total_services': 0, 'estimated_monthly_cost': 0},
            'pricing_reference': LOW_LEVEL_SERVICES
        }
    except Exception as e:
        print(f"Error discovering low-level services: {e}")
        return {
            'error': str(e),
            'services': [],
            'summary': {'total_services': 0, 'estimated_monthly_cost': 0},
            'pricing_reference': LOW_LEVEL_SERVICES
        }