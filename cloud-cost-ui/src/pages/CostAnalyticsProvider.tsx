"use client"

import React from "react"
import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { DashboardLayout } from "../components/layout/DashboardLayout"
import { Card } from "../components/ui/Card"
// To:// Replace the icon imports section with this:
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Power,
  Settings,
  MapPin,
  Tag,
  RefreshCw,
  AlertCircle,
  Loader2,
  Calendar,
  // Heater as Heatmap, // Remove or rename
  ChevronLeft,
  CheckCircle,
  XCircle,
  Database,
  Server,
  HardDrive,
  Cpu,
  Activity,
  Container,
  Cloud,
  // File as FileIcon, // Remove or rename
  Layers,
  Globe,
  Scale,
  Key,
  MessageSquare,
  Bell,
  Package,
  Lock,
  Eye,
  Trash2,
  Lightbulb,
  Zap,
  // Add these for resources:
  Code,
  Box,
  Sparkles,
  FileText,
  CircuitBoard,
  Monitor,
  Shield,
  Wrench,
  // Add Heatmap icon properly:
  Flame as Heatmap,
  // Add File icon properly:
  File as FileIcon,
  // Add missing icons for low-level services
  Network,
  ChevronUp,
  ChevronDown,
  Filter,
  Search,
  X,
} from "lucide-react"

type MenuItem =
  | "overview"
  | "connect"
  | "services"
  | "forecast"
  | "resources"  // Added resources menu
  | "anomalies"
  | "idle"
  | "rightsizing"
  | "savings"
  | "storage"
  | "regions"
  | "tags"
  | "heatmap"

type AwsInfo = {
  platform_account_id: string
  role_name: string
}

type DailySpend = {
  date: string
  amount: number
  day_name?: string
  full_date?: string
}

type Forecast = {
  thirtyDay: number
  sevenDay: number
}

type ServiceBreakdown = {
  service: string;
  amount: number;
  percentage: number;
}

type PaidResourceCategory = {
  name: string;
  description: string;
  cost_level: 'HIGH' | 'MEDIUM' | 'LOW';
  cost_driver: string;
  resources: any[];
  count: number;
  estimated_monthly_cost: number;
}

type PaidResourcesData = {
  cost_categories: {
    [key: string]: PaidResourceCategory;
  };
  summary: {
    total_paid_resources: number;
    high_cost_resources: number;
    medium_cost_resources: number;
    low_cost_resources: number;
    categories_found: number;
    timestamp: string;
  };
  raw_resources?: any;
  permissions_issues?: string[];
}

type CostAnalysisData = {
  high_risk_findings: Array<{
    category: string;
    issue: string;
    impact: string;
    recommendation: string;
    potential_savings: string;
  }>;
  medium_risk_findings: Array<{
    category: string;
    issue: string;
    impact: string;
    recommendation: string;
    potential_savings?: string;
  }>;
  low_risk_findings: Array<{
    category: string;
    issue: string;
    impact: string;
    recommendation: string;
    potential_savings?: string;
  }>;
  recommendations: string[];
  estimated_savings_potential: number;
  summary: {
    total_resources: number;
    high_cost_categories: number;
    medium_cost_categories: number;
    low_cost_categories: number;
  };
}

type ResourceData = {
  // Basic info
  total_resources: number;
  cached?: boolean;
  last_updated?: string;
  source?: string;
  permissions_issues?: string[];
  
  // EC2
  ec2: {
    total: number;
    running: number;
    stopped: number;
    avg_running_hours: number;
  };
  
  // S3
  s3: {
    total_buckets: number;
    avg_age_days: number;
  };
  
  // Lambda
  lambda: {
    total_functions: number;
  };
  
  // RDS
  rds: {
    total_instances: number;
  };
  
  // Make all other properties optional
  eks?: {
    total: number;
  };
  
  elasticache?: {
    total: number;
  };
  
  dynamodb?: {
    total: number;
  };
  
  redshift?: {
    total: number;
  };
  
  cloudfront?: {
    total: number;
  };
  
  load_balancers?: {
    total: number;
  };
  
  api_gateway?: {
    total: number;
  };
  
  sqs?: {
    total: number;
  };
  
  sns?: {
    total: number;
  };
  
  efs?: {
    total: number;
  };
  
  ecr?: {
    total: number;
  };
  
  elastic_beanstalk?: {
    total: number;
  };
  
  secretsmanager?: {
    total: number;
  };
  
  logs?: {
    total: number;
  };
  
  ssm?: {
    total: number;
  };
  
  config?: {
    total: number;
  };
  
  codebuild?: {
    total: number;
  };
  
  workspaces?: {
    total: number;
  };
  
  kinesis?: {
    total: number;
  };
  
  ebs?: {
    total: number;
  };
  
  // Add these missing properties
  opensearch?: {
    total: number;
  };
  
  route53?: {
    total: number;
  };
}

type ProviderData = {
  total_spend: number;
  today_spend: number;  // Actually yesterday's spend
  current_month_spend: number;
  current_month_name: string;
  monthly_change: number;
  forecast: Forecast;
  daily_spend: DailySpend[];
  service_breakdown?: ServiceBreakdown[];
}

type AwsAccount = {
  id: number
  aws_account_id: string
  role_arn: string
  external_id: string
  is_active: boolean
  created_at: string
  last_synced: string | null
}

// ============================================
// LOW-LEVEL SERVICES TYPES - NEW
// ============================================
interface LowLevelServicePricing {
  price_per_hour?: number;
  price_per_gb_month?: number;
  price_per_million?: number;
  price_per_gb?: number;
  price_per_vcpu_hour?: number;
  price_per_month?: number;
  unit: string;
}

interface LowLevelService extends LowLevelServicePricing {
  id: string;
  name: string;
  description: string;
}

interface LowLevelServiceResource {
  service_id: string;
  resource_id: string;
  resource_name: string;
  count: number;
  region: string;
  estimated_monthly_cost: number;
  details: Record<string, any>;
}

interface LowLevelServiceCategoryData {
  service_info: LowLevelService;
  category: string;
  resources: LowLevelServiceResource[];
  total_count: number;
  total_monthly_cost: number;
}

interface LowLevelServicesData {
  services_by_category: Record<string, LowLevelServiceCategoryData>;
  all_resources: LowLevelServiceResource[];
  summary: {
    total_services: number;
    estimated_monthly_cost: number;
    unique_service_types: number;
    unique_services_discovered: number;
    regions_scanned: string[];
    timestamp: string;
  };
  error?: string;
}

interface AWSAccount {
  id: number;
  account_id: string;
  account_name: string;
}

const CostAnalyticsProvider: React.FC = () => {
  const { provider } = useParams<{ provider: string }>()
  const navigate = useNavigate()
  const [selectedMenu, setSelectedMenu] = useState<MenuItem>("overview")

  // Auth token helper
  const getAuthToken = () => {
    return localStorage.getItem('token') || sessionStorage.getItem('token')
  }

  // Auth headers helper
  const getAuthHeaders = () => {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Token ${getAuthToken()}`
    }
  }

  // AWS Connection State
  const [awsInfo, setAwsInfo] = useState<AwsInfo | null>(null)
  const [externalId, setExternalId] = useState<string | null>(null)
  const [roleArn, setRoleArn] = useState("")
  const [awsLoading, setAwsLoading] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<string | null>(null)
  const [isConnectionSuccess, setIsConnectionSuccess] = useState<boolean>(false)

  // Cost Analytics State
  const [providerData, setProviderData] = useState<ProviderData>({
    total_spend: 0,
    today_spend: 0,
    current_month_spend: 0,
    current_month_name: '',
    monthly_change: 0,
    forecast: { thirtyDay: 0, sevenDay: 0 },
    daily_spend: [],
    service_breakdown: [],
  })

  // Resource State
  const [resourceData, setResourceData] = useState<ResourceData | null>(null)
  const [resourceLoading, setResourceLoading] = useState(false)

  const [error, setError] = useState<string | null>(null)
  const [accountId, setAccountId] = useState<number | null>(null)
  const [awsAccounts, setAwsAccounts] = useState<AwsAccount[]>([])
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string | null>(null)

  const [paidResources, setPaidResources] = useState<PaidResourcesData | null>(null);
  const [costAnalysis, setCostAnalysis] = useState<CostAnalysisData | null>(null);

  const fetchPaidResources = async () => {
    setLoading(true);
    try {
      const token = getAuthToken()
      const response = await fetch(`http://localhost:8000/resources/${accountId}/paid-resources/`, {
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) throw new Error('Failed to fetch paid resources');
      
      const data: PaidResourcesData = await response.json();
      console.log("Paid resources data:", data)
      setPaidResources(data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCostAnalysis = async () => {
    try {
      const token = getAuthToken()
      const response = await fetch(`http://localhost:8000/resources/${accountId}/cost-analysis/`, {
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) throw new Error('Failed to fetch cost analysis');
      
      const data: CostAnalysisData = await response.json();
      console.log("Cost analysis data:", data)
      setCostAnalysis(data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  useEffect(() => {
    if (accountId) {
      fetchPaidResources();
      fetchCostAnalysis();
    }
  }, [accountId]);

  // Check authentication on mount
  useEffect(() => {
    const token = getAuthToken()
    if (!token) {
      navigate('/login')
    }
  }, [navigate])

  // Fetch AWS platform info
  useEffect(() => {
    const fetchAwsInfo = async () => {
      try {
        const response = await fetch("http://localhost:8000/aws/info/", {
          headers: getAuthHeaders()
        })
        
        if (response.status === 401) {
          navigate('/login')
          return
        }
        
        if (!response.ok) {
          throw new Error("Failed to load AWS info")
        }
        
        const data = await response.json()
        setAwsInfo(data)
      } catch (error) {
        console.error("Error fetching AWS info:", error)
        setConnectionStatus("Failed to load AWS platform information")
      }
    }

    fetchAwsInfo()
  }, [navigate])

  // Fetch user's AWS accounts
  const fetchUserAccounts = async () => {
    const token = getAuthToken()
    if (!token) {
      navigate('/login')
      return
    }

    try {
      const response = await fetch("http://localhost:8000/aws-accounts/", {
        headers: getAuthHeaders()
      })

      if (response.status === 401) {
        navigate('/login')
        return
      }

      if (!response.ok) {
        throw new Error("Failed to fetch AWS accounts")
      }

      const accounts = await response.json()
      setAwsAccounts(accounts)
      
      // Set account ID based on provider param or use first account
      if (accounts.length > 0) {
        if (provider) {
          // Try to find account by AWS account ID
          const accountByAwsId = accounts.find((acc: AwsAccount) => 
            acc.aws_account_id === provider
          )
          
          // Try to find account by database ID
          const accountById = accounts.find((acc: AwsAccount) => 
            acc.id.toString() === provider
          )
          
          const selectedAccount = accountByAwsId || accountById || accounts[0]
          setAccountId(selectedAccount.id)
        } else {
          setAccountId(accounts[0].id)
        }
      }
    } catch (err: any) {
      console.error("Error fetching AWS accounts:", err)
      setError(err.message)
    }
  }

  // Initial load of AWS accounts
  useEffect(() => {
    fetchUserAccounts()
  }, [provider, navigate])

  // Fetch cost analytics when accountId is available
  const fetchCostAnalytics = async () => {
    if (!accountId) return

    const token = getAuthToken()
    if (!token) return

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`http://localhost:8000/aws-accounts/${accountId}/analytics/`, {
        headers: getAuthHeaders()
      })

      if (response.status === 401) {
        navigate('/login')
        return
      }

      if (!response.ok) {
        let errorMessage = "Failed to fetch cost analytics"
        try {
          const errorData = await response.json()
          console.error("Backend error details:", errorData)
          
          if (errorData.error && errorData.error.includes('max_digits')) {
            errorMessage = "Data formatting issue. Please sync your data again."
          } else {
            errorMessage = errorData.error || errorMessage
          }
        } catch (parseError) {
          console.error("Error parsing error response:", parseError)
        }
        throw new Error(errorMessage)
      }

      const data = await response.json()
      
      console.log("RAW API RESPONSE:", data)
      console.log("today_spend from API:", data.today_spend)
      console.log("Type of today_spend:", typeof data.today_spend)
      console.log("Service breakdown:", data.service_breakdown)
      
      setProviderData({
        total_spend: data.total_spend || 0,
        today_spend: data.today_spend || 0,
        current_month_spend: data.current_month_spend || 0,
        current_month_name: data.current_month_name || '',
        monthly_change: data.monthly_change || 0,
        forecast: data.forecast || { thirtyDay: 0, sevenDay: 0 },
        daily_spend: data.daily_spend || [],
        service_breakdown: data.service_breakdown || [],
      })

    } catch (err: any) {
      setError(err.message)
      console.error("Error fetching cost analytics:", err)
      
      // Set default data on error
      setProviderData({
        total_spend: 0,
        today_spend: 0,
        current_month_spend: 0,
        current_month_name: '',
        monthly_change: 0,
        forecast: { thirtyDay: 0, sevenDay: 0 },
        daily_spend: [],
        service_breakdown: [],
      })
    } finally {
      setLoading(false)
    }
  }

  // Fix the resource data functions at the top of your component (near other functions)
  const fetchResourceData = async (forceRefresh = false) => {
    setResourceLoading(true);
    try {
      const token = getAuthToken(); // Use the correct function
      if (!token) {
        navigate('/login');
        return;
      }

      const url = `http://localhost:8000/resources/${accountId}/resource_summary/${
        forceRefresh ? '?no_cache=true' : ''
      }`;
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.status === 401) {
        navigate('/login');
        return;
      }
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to fetch resource data');
      }
      
      const data = await response.json();
      setResourceData(data);
    } catch (error) {
      console.error('Error fetching resource data:', error);
      // Fix: Create a simple notification
      const message = error instanceof Error ? error.message : 'Failed to load resource data';
      setStatus(message);
    } finally {
      setResourceLoading(false);
    }
  };

  const clearResourceCache = async () => {
    try {
      const token = getAuthToken(); // Use the correct function
      if (!token) {
        navigate('/login');
        return;
      }

      const response = await fetch(`http://localhost:8000/resources/${accountId}/clear_cache/`, {
        method: 'POST',
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.status === 401) {
        navigate('/login');
        return;
      }
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to clear cache');
      }
      
      // Simple notification
      setStatus('Cache cleared successfully');
      setIsConnectionSuccess(true);
      
      // Refresh data after clearing cache
      fetchResourceData(true);
    } catch (error) {
      console.error('Error clearing cache:', error);
      const message = error instanceof Error ? error.message : 'Failed to clear cache';
      setStatus(message);
      setIsConnectionSuccess(false);
    }
  };

  // Manual refresh function
  const refreshAnalytics = async () => {
    if (!accountId) return

    const token = getAuthToken()
    if (!token) return

    setLoading(true)
    setError(null)
    setStatus(null)

    try {
      // Trigger manual sync
      const syncResponse = await fetch(`http://localhost:8000/aws-accounts/${accountId}/sync/`, {
        method: "POST",
        headers: getAuthHeaders()
      })

      if (!syncResponse.ok) {
        const errorData = await syncResponse.json()
        console.warn("Sync triggered but may have issues:", errorData)
      }

      // Wait for sync to process
      await new Promise(resolve => setTimeout(resolve, 3000))

      // Fetch updated analytics
      await fetchCostAnalytics()
      
      setStatus("Data refreshed successfully!")
      setTimeout(() => setStatus(null), 3000)
    } catch (err: any) {
      setError(err.message)
      console.error("Error refreshing analytics:", err)
    } finally {
      setLoading(false)
    }
  }

  // Load data based on selected menu
  useEffect(() => {
    if (!accountId) return

    if (selectedMenu === "overview" || selectedMenu === "services") {
      fetchCostAnalytics()
    } else if (selectedMenu === "resources") {
      fetchResourceData()
    }
  }, [accountId, selectedMenu])

  // Generate External ID
  const createRoleInAws = async () => {
    setAwsLoading(true)
    setConnectionStatus(null)
    setIsConnectionSuccess(false)

    try {
      const res = await fetch("http://localhost:8000/aws/generate-external-id/", {
        method: "POST",
        headers: getAuthHeaders()
      })
      
      if (res.status === 401) {
        navigate('/login')
        return
      }
      
      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.error || "Failed to generate External ID")
      }
      
      const data = await res.json()
      setExternalId(data.external_id)
      setConnectionStatus("External ID generated successfully! Follow the steps below.")
      setIsConnectionSuccess(true)
    } catch (err: any) {
      setConnectionStatus(`❌ ${err.message}`)
      setIsConnectionSuccess(false)
    } finally {
      setAwsLoading(false)
    }
  }

  // Connect AWS Account
  const connectAccount = async () => {
    if (!roleArn.trim()) {
      setConnectionStatus("❌ Please enter a Role ARN")
      setIsConnectionSuccess(false)
      return
    }

    setAwsLoading(true)
    setConnectionStatus(null)

    try {
      const res = await fetch("http://localhost:8000/aws/connect-account/", {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ role_arn: roleArn }),
      })

      if (res.status === 401) {
        navigate('/login')
        return
      }

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.error || "Failed to connect account")
      }

      const data = await res.json()
      setConnectionStatus(`✅ ${data.message || "AWS account connected successfully!"}`)
      setIsConnectionSuccess(true)
      
      // Clear form
      setRoleArn("")
      setExternalId(null)
      
      // Refresh accounts list
      setTimeout(() => {
        fetchUserAccounts()
      }, 1000)
    } catch (err: any) {
      setConnectionStatus(`❌ ${err.message}`)
      setIsConnectionSuccess(false)
    } finally {
      setAwsLoading(false)
    }
  }

  // Manual instructions
  const manualInstructions = {
    steps: [
      {
        title: "Step 1: Create the Policy",
        instructions: [
          "Navigate to IAM → Policies → Create Policy",
          "Click the 'JSON' tab",
          "Paste the policy JSON (shown below)",
          "Name it: CloudCostReadOnlyPolicy",
          "Click 'Create Policy'"
        ]
      },
      {
        title: "Step 2: Create the Role",
        instructions: [
          "Navigate to IAM → Roles → Create Role",
          "Select 'Another AWS account'",
          `Enter Account ID: ${awsInfo?.platform_account_id || "026395503692"}`,
          "✓ Check 'Require external ID'",
          `Paste External ID: ${externalId || "[Will appear after clicking 'Create Role in AWS']"}`,
          "Click 'Next'"
        ]
      },
      {
        title: "Step 3: Attach the Policy",
        instructions: [
          "On the 'Add permissions' page:",
          "Search for 'CloudCostReadOnlyPolicy'",
          "✓ Check the box next to it",
          "Click 'Next'"
        ]
      },
      {
        title: "Step 4: Complete & Copy ARN",
        instructions: [
          "Name the role: CloudCostReadOnlyRole",
          "Click 'Create Role'",
          "Copy the Role ARN (starts with 'arn:aws:iam::')"
        ]
      }
    ]
  }

  // Policy JSON
  const policyJson = `{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetCostForecast",
        "ce:GetDimensionValues",
        "organizations:ListAccounts",
        "ec2:Describe*",
        "s3:ListAllMyBuckets",
        "rds:Describe*",
        "iam:List*",
        "cloudwatch:GetMetricData"
      ],
      "Resource": "*"
    }
  ]
}`

  const menuItems: { id: MenuItem; label: string; icon: React.ReactNode }[] = [
    { id: "connect", label: "Connect Account", icon: <Settings className="w-4 h-4" /> },
    { id: "overview", label: "Total Spend", icon: <DollarSign className="w-4 h-4" /> },
    { id: "services", label: "Service Breakdown", icon: <Settings className="w-4 h-4" /> },
    { id: "resources", label: "Resources", icon: <Server className="w-4 h-4" /> },
    { id: "forecast", label: "Forecast", icon: <TrendingUp className="w-4 h-4" /> },
    { id: "anomalies", label: "Anomaly Detection", icon: <AlertTriangle className="w-4 h-4" /> },
    { id: "idle", label: "Idle Resources", icon: <Power className="w-4 h-4" /> },
    { id: "rightsizing", label: "Rightsizing", icon: <Settings className="w-4 h-4" /> },
    { id: "savings", label: "Savings Plans", icon: <DollarSign className="w-4 h-4" /> },
    { id: "storage", label: "Storage Optimization", icon: <Settings className="w-4 h-4" /> },
    { id: "regions", label: "Cost by Region", icon: <MapPin className="w-4 h-4" /> },
    { id: "tags", label: "Cost by Tag", icon: <Tag className="w-4 h-4" /> },
    { id: "heatmap", label: "Heatmap", icon: <Heatmap className="w-4 h-4" /> },
  ]

  // Get selected account name
  const selectedAccount = awsAccounts.find(acc => acc.id === accountId)
  const accountName = selectedAccount ? `AWS Account: ${selectedAccount.aws_account_id}` : "Loading..."

  // Get yesterday's date for display
  const getYesterday = () => {
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    return yesterday.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
  }

  const getResourceCategoryData = () => {
    if (!paidResources?.cost_categories) return [];
    
    return Object.entries(paidResources.cost_categories)
      .filter(([_, data]) => data.count > 0)
      .sort((a, b) => b[1].count - a[1].count);
  };

  const getCostLevelColor = (level: string) => {
    switch(level) {
      case 'HIGH': return 'text-red-600 dark:text-red-400';
      case 'MEDIUM': return 'text-yellow-600 dark:text-yellow-400';
      case 'LOW': return 'text-green-600 dark:text-green-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getCostLevelBgColor = (level: string) => {
    switch(level) {
      case 'HIGH': return 'bg-red-100 dark:bg-red-900/20';
      case 'MEDIUM': return 'bg-yellow-100 dark:bg-yellow-900/20';
      case 'LOW': return 'bg-green-100 dark:bg-green-900/20';
      default: return 'bg-gray-100 dark:bg-gray-900/20';
    }
  };

  const getResourceIcon = (categoryKey: string) => {
    const icons: {[key: string]: React.ReactNode} = {
      'ec2': <Cpu className="w-5 h-5" />,
      'lambda': <Code className="w-5 h-5" />,
      'eks': <Container className="w-5 h-5" />,
      'rds': <Database className="w-5 h-5" />,
      'dynamodb': <Box className="w-5 h-5" />,
      'elasticache': <Zap className="w-5 h-5" />,
      'redshift': <Sparkles className="w-5 h-5" />,
      's3': <HardDrive className="w-5 h-5" />,
      'efs': <FileText className="w-5 h-5" />,
      'ebs': <HardDrive className="w-5 h-5" />,
      'cloudfront': <Globe className="w-5 h-5" />,
      'load_balancers': <Scale className="w-5 h-5" />,
      'api_gateway': <Key className="w-5 h-5" />,
      'sqs': <MessageSquare className="w-5 h-5" />,
      'sns': <Bell className="w-5 h-5" />,
      'ecr': <Layers className="w-5 h-5" />,
      'elastic_beanstalk': <Package className="w-5 h-5" />,
      'secrets_manager': <Lock className="w-5 h-5" />,
      'cloudwatch': <Eye className="w-5 h-5" />,
      'codebuild': <CircuitBoard className="w-5 h-5" />,
      'workspaces': <Monitor className="w-5 h-5" />,
      'kinesis': <Wrench className="w-5 h-5" />,
      'config': <Shield className="w-5 h-5" />,
      'ssm': <Wrench className="w-5 h-5" />,
    };
    
    return icons[categoryKey] || <Server className="w-5 h-5" />;
  };

  return (
    <DashboardLayout>
      <div className="flex h-[calc(100vh-4rem)]">
        {/* LEFT SIDEBAR - Menu */}
        <div className="w-72 border-r border-border bg-card/50 overflow-y-auto">
          <div className="p-4">
            <button
              onClick={() => navigate("/cost-analytics")}
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Back to Providers
            </button>

            {/* Account Selector */}
            <div className="mb-6">
              <label htmlFor="account-select" className="block text-sm font-medium text-foreground mb-2">
                Select AWS Account
              </label>
              <select
                id="account-select"
                title="Select AWS Account"
                value={accountId || ""}
                onChange={(e) => setAccountId(Number(e.target.value))}
                className="w-full px-3 py-2 bg-input border border-border rounded-lg text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                disabled={awsAccounts.length === 0}
              >
                {awsAccounts.length === 0 ? (
                  <option value="">No accounts connected</option>
                ) : (
                  <>
                    <option value="">Select an account</option>
                    {awsAccounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.aws_account_id} {account.is_active ? "✓" : "⚠"}
                      </option>
                    ))}
                  </>
                )}
              </select>
              <div className="mt-2 text-xs text-muted-foreground">
                {awsAccounts.length === 0 
                  ? "Connect an AWS account to view analytics" 
                  : `${awsAccounts.length} account(s) connected`}
              </div>
            </div>

            {/* Menu Items */}
            <div className="space-y-1">
              {menuItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setSelectedMenu(item.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                    selectedMenu === item.id
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  {item.icon}
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT CONTENT */}
        <div className="flex-1 overflow-y-auto p-8">
          <div className="max-w-6xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
              <div>
                <h1 className="text-3xl font-bold text-foreground mb-2">
                  {accountName}
                </h1>
                <p className="text-muted-foreground">Detailed cost insights and optimization recommendations</p>
              </div>
              {selectedMenu !== "connect" && accountId && (
                <button
                  onClick={refreshAnalytics}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50 transition disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                  Refresh
                </button>
              )}
            </div>

            {/* Status Messages */}
            {status && (
              <div className={`p-4 rounded-lg ${isConnectionSuccess ? 'bg-success/10 border border-success/20' : 'bg-error/10 border border-error/20'}`}>
                <div className="flex items-center gap-2">
                  {isConnectionSuccess ? (
                    <CheckCircle className="w-5 h-5 text-success" />
                  ) : (
                    <XCircle className="w-5 h-5 text-error" />
                  )}
                  <span className={isConnectionSuccess ? "text-success" : "text-error"}>
                    {status}
                  </span>
                </div>
              </div>
            )}

            {connectionStatus && (
              <div className={`p-4 rounded-lg ${isConnectionSuccess ? 'bg-success/10 border border-success/20' : 'bg-error/10 border border-error/20'}`}>
                <div className="flex items-center gap-2">
                  {isConnectionSuccess ? (
                    <CheckCircle className="w-5 h-5 text-success" />
                  ) : (
                    <XCircle className="w-5 h-5 text-error" />
                  )}
                  <span className={isConnectionSuccess ? "text-success" : "text-error"}>
                    {connectionStatus}
                  </span>
                </div>
              </div>
            )}

            {error && (
              <div className="p-4 bg-error/10 border border-error/20 rounded-lg">
                <div className="flex items-center gap-2 text-error">
                  <AlertCircle className="w-5 h-5" />
                  <span>{error}</span>
                </div>
              </div>
            )}

            {/* Loading State */}
            {loading && !providerData.daily_spend.length && selectedMenu === "overview" && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
                <span className="ml-2">Loading cost data...</span>
              </div>
            )}

            {/* ============================================ */}
            {/* UPDATED SERVICES SECTION - WITH LOW-LEVEL SERVICES */}
            {/* ============================================ */}
            
            {selectedMenu === "services" && accountId && (
              <div className="space-y-6">
                {/* HIGH-LEVEL SERVICE BREAKDOWN (YOUR EXISTING CODE - UNCHANGED) */}
                <Card className="p-6">
                  <div className="flex justify-between items-center mb-6">
                    <div>
                      <h3 className="text-2xl font-bold text-foreground">Service Breakdown</h3>
                      <p className="text-muted-foreground">
                        Detailed cost breakdown by AWS service for {providerData.current_month_name}
                      </p>
                    </div>
                    <button
                      onClick={refreshAnalytics}
                      disabled={loading}
                      className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
                    >
                      {loading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <RefreshCw className="w-4 h-4" />
                      )}
                      Refresh
                    </button>
                  </div>

                  {providerData.service_breakdown && providerData.service_breakdown.length > 0 ? (
                    <>
                      {/* Summary Cards */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                        <Card className="p-4">
                          <p className="text-sm text-muted-foreground mb-1">Total Services</p>
                          <p className="text-2xl font-bold text-foreground">
                            {providerData.service_breakdown.length}
                          </p>
                        </Card>
                        <Card className="p-4">
                          <p className="text-sm text-muted-foreground mb-1">Top Service</p>
                          <p className="text-xl font-bold text-foreground truncate">
                            {providerData.service_breakdown[0]?.service || 'N/A'}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            ${providerData.service_breakdown[0]?.amount?.toFixed(2) || '0.00'}
                          </p>
                        </Card>
                        <Card className="p-4">
                          <p className="text-sm text-muted-foreground mb-1">This Month Total</p>
                          <p className="text-2xl font-bold text-foreground">
                            ${providerData.current_month_spend.toLocaleString(undefined, {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2
                            })}
                          </p>
                        </Card>
                      </div>

                      {/* Service Table */}
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead>
                            <tr className="border-b border-border">
                              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Service</th>
                              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Amount</th>
                              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Percentage</th>
                              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Actions</th>
                            </tr>
                          </thead>
                          <tbody>
                            {providerData.service_breakdown.map((service, index) => (
                              <tr key={index} className="border-b border-border hover:bg-muted/50">
                                <td className="py-3 px-4">
                                  <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                                      <Settings className="w-4 h-4 text-primary" />
                                    </div>
                                    <span className="font-medium">{service.service}</span>
                                  </div>
                                </td>
                                <td className="py-3 px-4">
                                  <span className="font-bold">
                                    ${service.amount.toLocaleString(undefined, {
                                      minimumFractionDigits: 2,
                                      maximumFractionDigits: 2
                                    })}
                                  </span>
                                </td>
                                <td className="py-3 px-4">
                                  <div className="flex items-center gap-2">
                                    <div className="w-24 bg-muted rounded-full h-2">
                                      <div 
                                        className="bg-primary rounded-full h-2"
                                        style={{ width: `${Math.min(service.percentage, 100)}%` }}
                                      />
                                    </div>
                                    <span className="text-sm font-medium">{service.percentage.toFixed(1)}%</span>
                                  </div>
                                </td>
                                <td className="py-3 px-4">
                                  <button
                                    className="text-sm text-primary hover:underline"
                                    onClick={() => {
                                      console.log(`Analyze ${service.service}`)
                                    }}
                                  >
                                    Analyze
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      {/* Chart Visualization - Your existing chart code */}
                      <div className="space-y-4">
                        <div className="relative h-72">
                          {/* Y-axis labels */}
                          <div className="absolute left-0 top-0 bottom-0 w-12 flex flex-col justify-between text-xs text-muted-foreground py-8">
                            {(() => {
                              const amounts = providerData.service_breakdown?.slice(0, 8).map(s => s.amount) || [];
                              const maxAmount = Math.max(...amounts, 1);
                              const steps = [1, 0.75, 0.5, 0.25, 0];
                              return steps.map((step, i) => (
                                <div key={i} className="flex items-center">
                                  <span className="mr-1 text-[10px]">${(maxAmount * step).toFixed(2)}</span>
                                  <div className="flex-1 border-t border-border/30"></div>
                                </div>
                              ));
                            })()}
                          </div>
                          
                          <div className="ml-12 h-full">
                            <div className="h-full flex items-end justify-between gap-3 px-2">
                              {providerData.service_breakdown?.slice(0, 8).map((service, index) => {
                                const amounts = providerData.service_breakdown?.slice(0, 8).map(s => s.amount) || [];
                                const maxAmount = Math.max(...amounts, 1);
                                const heightPercentage = service.amount === 0 
                                  ? 5 
                                  : Math.max((service.amount / maxAmount) * 90, 5);
                                
                                const colors = [
                                  'bg-gradient-to-t from-blue-500 to-blue-400 hover:from-blue-600 hover:to-blue-500',
                                  'bg-gradient-to-t from-green-500 to-green-400 hover:from-green-600 hover:to-green-500',
                                  'bg-gradient-to-t from-purple-500 to-purple-400 hover:from-purple-600 hover:to-purple-500',
                                  'bg-gradient-to-t from-orange-500 to-orange-400 hover:from-orange-600 hover:to-orange-500',
                                  'bg-gradient-to-t from-red-500 to-red-400 hover:from-red-600 hover:to-red-500',
                                  'bg-gradient-to-t from-pink-500 to-pink-400 hover:from-pink-600 hover:to-pink-500',
                                  'bg-gradient-to-t from-cyan-500 to-cyan-400 hover:from-cyan-600 hover:to-cyan-500',
                                  'bg-gradient-to-t from-yellow-500 to-yellow-400 hover:from-yellow-600 hover:to-yellow-500'
                                ];
                                
                                const barColor = colors[index % colors.length];
                                const barWidth = index === 0 || index === 7 ? 'w-2/3' : 
                                                index === 1 || index === 6 ? 'w-3/4' : 
                                                'w-4/5';
                                
                                return (
                                  <div key={index} className="flex-1 flex flex-col items-center justify-end group h-full">
                                    <div className="relative flex flex-col items-center w-full">
                                      <div className="mb-2 text-xs font-semibold text-foreground/90 bg-card/70 px-2 py-1 rounded border border-border/30">
                                        ${service.amount.toFixed(2)}
                                      </div>
                                      <div className="mb-1 text-[10px] font-medium text-muted-foreground">
                                        {service.percentage.toFixed(1)}%
                                      </div>
                                      <div className="w-full flex items-end" style={{ height: 'calc(100% - 4rem)' }}>
                                        <div
                                          className={`relative mx-auto rounded-t-lg transition-all duration-500 ${barColor} ${barWidth}
                                            group-hover:w-11/12 group-hover:shadow-xl group-hover:scale-105`}
                                          style={{ height: `${heightPercentage}%`, minHeight: '24px' }}
                                        >
                                          <div className="absolute inset-x-0 top-0 h-1/3 rounded-t-lg bg-white/30"></div>
                                          <div className="absolute -top-20 left-1/2 -translate-x-1/2 bg-card border border-border px-4 py-3 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10 shadow-2xl pointer-events-none min-w-[200px]">
                                            <div className="font-semibold text-foreground text-sm mb-2">
                                              {service.service}
                                            </div>
                                            <div className="text-primary font-bold text-lg mb-1">
                                              ${service.amount.toLocaleString(undefined, {
                                                minimumFractionDigits: 2,
                                                maximumFractionDigits: 2
                                              })}
                                            </div>
                                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                              <div className="h-2 flex-1 bg-muted rounded-full overflow-hidden">
                                                <div 
                                                  className="h-full bg-primary rounded-full"
                                                  style={{ width: `${Math.min(service.percentage, 100)}%` }}
                                                />
                                              </div>
                                              <span className="font-medium">{service.percentage.toFixed(1)}% of total</span>
                                            </div>
                                            {service.percentage > 30 && (
                                              <div className="mt-2 text-xs text-orange-500 font-medium">
                                                ⚠️ Major cost driver
                                              </div>
                                            )}
                                          </div>
                                        </div>
                                      </div>
                                    </div>
                                    <div className="mt-3 w-full text-center pt-2 border-t border-border/30">
                                      <div className="text-sm font-semibold text-foreground truncate px-1" title={service.service}>
                                        {service.service.length > 15 
                                          ? service.service.substring(0, 13) + '...' 
                                          : service.service}
                                      </div>
                                      <div className="text-xs text-muted-foreground mt-1">#{index + 1}</div>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                            <div className="absolute left-0 right-0 bottom-10 border-t-2 border-border"></div>
                          </div>
                        </div>
                        
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                          <div className="flex items-center gap-2 p-3 bg-card/30 rounded-lg border border-border/20">
                            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                            <div>
                              <div className="text-xs text-muted-foreground">Top Service</div>
                              <div className="font-semibold text-foreground truncate" title={providerData.service_breakdown[0]?.service}>
                                {providerData.service_breakdown[0]?.service.split(' ')[0] || 'N/A'}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 p-3 bg-card/30 rounded-lg border border-border/20">
                            <div className="w-3 h-3 rounded-full bg-green-500"></div>
                            <div>
                              <div className="text-xs text-muted-foreground">Top Service Cost</div>
                              <div className="font-semibold text-foreground">
                                ${providerData.service_breakdown[0]?.amount?.toFixed(2) || '0.00'}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 p-3 bg-card/30 rounded-lg border border-border/20">
                            <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                            <div>
                              <div className="text-xs text-muted-foreground">Top Service %</div>
                              <div className="font-semibold text-foreground">
                                {providerData.service_breakdown[0]?.percentage?.toFixed(1) || '0.0'}%
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 p-3 bg-card/30 rounded-lg border border-border/20">
                            <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                            <div>
                              <div className="text-xs text-muted-foreground">Services Tracked</div>
                              <div className="font-semibold text-foreground">
                                {providerData.service_breakdown?.length || 0}
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        {providerData.service_breakdown && providerData.service_breakdown[0]?.percentage > 50 && (
                          <div className="p-4 bg-orange-50 dark:bg-orange-900/10 border border-orange-200 dark:border-orange-800/30 rounded-lg">
                            <div className="flex items-start gap-3">
                              <AlertTriangle className="w-5 h-5 text-orange-500 flex-shrink-0 mt-0.5" />
                              <div>
                                <h5 className="font-medium text-foreground">Cost Concentration Warning</h5>
                                <p className="text-sm text-muted-foreground mt-1">
                                  Top service ({providerData.service_breakdown[0]?.service}) accounts for {providerData.service_breakdown[0]?.percentage.toFixed(1)}% of total costs.
                                  Consider reviewing this service for optimization opportunities.
                                </p>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </>
                  ) : (
                    <div className="text-center py-12">
                      <Settings className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-50" />
                      <h4 className="text-lg font-semibold text-foreground mb-2">No Service Data</h4>
                      <p className="text-muted-foreground mb-6">
                        {loading ? 'Loading service breakdown...' : 'Service breakdown data is not available yet'}
                      </p>
                      <button onClick={refreshAnalytics} className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:opacity-90">
                        {loading ? 'Loading...' : 'Sync Account Data'}
                      </button>
                    </div>
                  )}
                </Card>

                {/* LOW-LEVEL SERVICES SECTION - FIXED */}
                {accountId && <LowLevelServicesComponent accountId={accountId} />}
              </div>
            )}

            {/* Resources View - YOUR EXISTING CODE (UNCHANGED) */}
            {selectedMenu === "resources" && accountId && (
              <div className="space-y-6">
                {/* Paid Resources Overview */}
                <Card className="p-6">
                  <div className="flex justify-between items-center mb-6">
                    <div>
                      <h3 className="text-2xl font-bold text-foreground">Paid Resources Overview</h3>
                      <p className="text-muted-foreground">
                        All AWS resources that can incur charges, categorized by cost impact
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={fetchPaidResources}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
                      >
                        {loading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <RefreshCw className="w-4 h-4" />
                        )}
                        Refresh
                      </button>
                    </div>
                  </div>

                  {loading ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="w-8 h-8 animate-spin text-primary" />
                      <span className="ml-2">Loading resource data...</span>
                    </div>
                  ) : paidResources ? (
                    <>
                      {/* Summary Cards */}
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                        <Card className="p-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center">
                              <Server className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                            </div>
                            <div>
                              <p className="text-sm text-muted-foreground">Total Paid Resources</p>
                              <p className="text-2xl font-bold text-foreground">
                                {paidResources.summary?.total_paid_resources || 0}
                              </p>
                            </div>
                          </div>
                        </Card>
                        <Card className="p-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-red-100 dark:bg-red-900/20 flex items-center justify-center">
                              <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
                            </div>
                            <div>
                              <p className="text-sm text-muted-foreground">High Cost Resources</p>
                              <p className="text-2xl font-bold text-foreground">
                                {paidResources.summary?.high_cost_resources || 0}
                              </p>
                            </div>
                          </div>
                        </Card>
                        <Card className="p-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-yellow-100 dark:bg-yellow-900/20 flex items-center justify-center">
                              <Activity className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
                            </div>
                            <div>
                              <p className="text-sm text-muted-foreground">Medium Cost Resources</p>
                              <p className="text-2xl font-bold text-foreground">
                                {paidResources.summary?.medium_cost_resources || 0}
                              </p>
                            </div>
                          </div>
                        </Card>
                        <Card className="p-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/20 flex items-center justify-center">
                              <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                            </div>
                            <div>
                              <p className="text-sm text-muted-foreground">Low Cost Resources</p>
                              <p className="text-2xl font-bold text-foreground">
                                {paidResources.summary?.low_cost_resources || 0}
                              </p>
                            </div>
                          </div>
                        </Card>
                      </div>

                      {/* Resource Categories Grid */}
                      <div className="mb-6">
                        <h4 className="text-lg font-semibold text-foreground mb-4">
                          Resource Categories ({paidResources.summary?.categories_found || 0} categories found)
                        </h4>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                          {getResourceCategoryData().map(([categoryKey, category]) => (
                            <Card key={categoryKey} className="p-4 hover:shadow-lg transition-shadow">
                              <div className="flex justify-between items-start mb-3">
                                <div className="flex items-center gap-3">
                                  <div className={`w-10 h-10 rounded-lg ${getCostLevelBgColor(category.cost_level)} flex items-center justify-center`}>
                                    {getResourceIcon(categoryKey)}
                                  </div>
                                  <div>
                                    <h5 className="font-semibold text-foreground">{category.name}</h5>
                                    <span className={`text-xs font-medium ${getCostLevelColor(category.cost_level)}`}>
                                      {category.cost_level} cost • {category.count} resources
                                    </span>
                                  </div>
                                </div>
                              </div>
                              
                              <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                                {category.description}
                              </p>
                              
                              <div className="space-y-2">
                                <div className="flex justify-between text-sm">
                                  <span className="text-muted-foreground">Cost Driver:</span>
                                  <span className="font-medium text-foreground">{category.cost_driver}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                  <span className="text-muted-foreground">Estimated Monthly Cost:</span>
                                  <span className="font-bold text-foreground">
                                    ${category.estimated_monthly_cost.toFixed(2)}
                                  </span>
                                </div>
                              </div>
                              
                              <div className="mt-4 pt-4 border-t">
                                <button
                                  onClick={() => {
                                    console.log('Show details for:', categoryKey);
                                  }}
                                  className="w-full text-sm text-primary hover:underline"
                                >
                                  View {category.count} resources →
                                </button>
                              </div>
                            </Card>
                          ))}
                        </div>
                      </div>

                      {/* Cost Analysis Section */}
                      {costAnalysis && (
                        <div className="space-y-6">
                          <h4 className="text-lg font-semibold text-foreground">Cost Analysis & Recommendations</h4>
                          
                          {/* High Risk Findings */}
                          {costAnalysis.high_risk_findings && costAnalysis.high_risk_findings.length > 0 && (
                            <Card className="border-red-200 dark:border-red-800">
                              <div className="p-4">
                                <div className="flex items-center gap-2 mb-3">
                                  <AlertTriangle className="w-5 h-5 text-red-600" />
                                  <h5 className="font-semibold text-red-600">High Risk Findings</h5>
                                </div>
                                <div className="space-y-3">
                                  {costAnalysis.high_risk_findings.map((finding: any, index: number) => (
                                    <div key={index} className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                                      <div className="flex justify-between items-start mb-2">
                                        <span className="font-medium text-red-800 dark:text-red-300">
                                          {finding.category}: {finding.issue}
                                        </span>
                                        <span className="font-bold text-red-600">{finding.potential_savings}</span>
                                      </div>
                                      <p className="text-sm text-red-700 dark:text-red-400 mb-2">{finding.impact}</p>
                                      <p className="text-sm font-medium text-red-800 dark:text-red-300">
                                        Recommendation: {finding.recommendation}
                                      </p>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </Card>
                          )}

                          {/* Medium Risk Findings */}
                          {costAnalysis.medium_risk_findings && costAnalysis.medium_risk_findings.length > 0 && (
                            <Card className="border-yellow-200 dark:border-yellow-800">
                              <div className="p-4">
                                <div className="flex items-center gap-2 mb-3">
                                  <AlertCircle className="w-5 h-5 text-yellow-600" />
                                  <h5 className="font-semibold text-yellow-600">Medium Risk Findings</h5>
                                </div>
                                <div className="space-y-3">
                                  {costAnalysis.medium_risk_findings.map((finding: any, index: number) => (
                                    <div key={index} className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                                      <div className="flex justify-between items-start mb-2">
                                        <span className="font-medium text-yellow-800 dark:text-yellow-300">
                                          {finding.category}: {finding.issue}
                                        </span>
                                      </div>
                                      <p className="text-sm text-yellow-700 dark:text-yellow-400 mb-2">{finding.impact}</p>
                                      <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
                                        Recommendation: {finding.recommendation}
                                      </p>
                                      {finding.potential_savings && (
                                        <div className="mt-2 text-sm font-bold text-yellow-700">
                                          Potential Savings: {finding.potential_savings}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </Card>
                          )}

                          {/* Overall Recommendations */}
                          {costAnalysis.recommendations && costAnalysis.recommendations.length > 0 && (
                            <Card>
                              <div className="p-4">
                                <div className="flex items-center gap-2 mb-3">
                                  <Lightbulb className="w-5 h-5 text-primary" />
                                  <h5 className="font-semibold text-foreground">Optimization Recommendations</h5>
                                </div>
                                <ul className="space-y-2">
                                  {costAnalysis.recommendations.map((rec: string, index: number) => (
                                    <li key={index} className="flex items-start gap-2">
                                      <CheckCircle className="w-4 h-4 text-green-500 mt-1 flex-shrink-0" />
                                      <span className="text-foreground">{rec}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            </Card>
                          )}
                        </div>
                      )}

                      {/* Permissions Issues */}
                      {paidResources.permissions_issues && paidResources.permissions_issues.length > 0 && (
                        <Card className="border-red-200 dark:border-red-800 mt-6">
                          <div className="p-4">
                            <div className="flex items-center gap-2 mb-3">
                              <AlertTriangle className="w-5 h-5 text-red-600" />
                              <h5 className="font-semibold text-red-600">Permissions Issues</h5>
                            </div>
                            <p className="text-sm text-muted-foreground mb-3">
                              Some services couldn't be accessed due to missing IAM permissions
                            </p>
                            <ul className="space-y-2">
                              {paidResources.permissions_issues.map((issue: string, index: number) => (
                                <li key={index} className="flex items-center gap-2 text-sm">
                                  <XCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                                  <span className="text-red-600 dark:text-red-400">{issue}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        </Card>
                      )}
                    </>
                  ) : (
                    <div className="text-center py-12">
                      <Server className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-50" />
                      <h4 className="text-lg font-semibold text-foreground mb-2">No Paid Resource Data</h4>
                      <p className="text-muted-foreground mb-6">
                        Paid resource data is not available. This could be due to permission issues or no resources found.
                      </p>
                      <button onClick={fetchPaidResources} className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:opacity-90">
                        Load Paid Resources
                      </button>
                    </div>
                  )}
                </Card>

                {/* Traditional Resource Summary */}
                <Card className="p-6">
                  <div className="flex justify-between items-center mb-6">
                    <div>
                      <h3 className="text-2xl font-bold text-foreground">Resource Summary</h3>
                      <p className="text-muted-foreground">
                        Detailed count of AWS resources by service
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => fetchResourceData(true)}
                        disabled={resourceLoading}
                        className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
                      >
                        {resourceLoading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <RefreshCw className="w-4 h-4" />
                        )}
                        Refresh
                      </button>
                      <button
                        onClick={clearResourceCache}
                        className="flex items-center gap-2 px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:opacity-90"
                      >
                        <Trash2 className="w-4 h-4" />
                        Clear Cache
                      </button>
                    </div>
                  </div>

                  {resourceLoading ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="w-8 h-8 animate-spin text-primary" />
                      <span className="ml-2">Loading resource summary...</span>
                    </div>
                  ) : resourceData ? (
                    <>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                        <Card className="p-4">
                          <h4 className="font-semibold text-lg mb-3 flex items-center gap-2">
                            <Cpu className="w-5 h-5" /> Compute
                          </h4>
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">EC2 Instances</span>
                              <span className="font-bold">{resourceData.ec2?.total || 0}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Lambda Functions</span>
                              <span className="font-bold">{resourceData.lambda?.total_functions || 0}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">EKS Clusters</span>
                              <span className="font-bold">{resourceData.eks?.total || 0}</span>
                            </div>
                          </div>
                        </Card>

                        <Card className="p-4">
                          <h4 className="font-semibold text-lg mb-3 flex items-center gap-2">
                            <Database className="w-5 h-5" /> Databases
                          </h4>
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">RDS Instances</span>
                              <span className="font-bold">{resourceData.rds?.total_instances || 0}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">DynamoDB Tables</span>
                              <span className="font-bold">{resourceData.dynamodb?.total || 0}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">ElastiCache Clusters</span>
                              <span className="font-bold">{resourceData.elasticache?.total || 0}</span>
                            </div>
                          </div>
                        </Card>

                        <Card className="p-4">
                          <h4 className="font-semibold text-lg mb-3 flex items-center gap-2">
                            <HardDrive className="w-5 h-5" /> Storage
                          </h4>
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">S3 Buckets</span>
                              <span className="font-bold">{resourceData.s3?.total_buckets || 0}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">EFS File Systems</span>
                              <span className="font-bold">{resourceData.efs?.total || 0}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">EBS Volumes</span>
                              <span className="font-bold">{resourceData.ebs?.total || 0}</span>
                            </div>
                          </div>
                        </Card>
                      </div>

                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead>
                            <tr className="border-b border-border">
                              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Service</th>
                              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Resource Count</th>
                              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Status</th>
                              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Details</th>
                            </tr>
                          </thead>
                          <tbody>
                            {resourceData.ec2?.total > 0 && (
                              <tr className="border-b border-border hover:bg-muted/50">
                                <td className="py-3 px-4">
                                  <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-lg bg-green-100 dark:bg-green-900/20 flex items-center justify-center">
                                      <Cpu className="w-4 h-4 text-green-600" />
                                    </div>
                                    <span className="font-medium">EC2 Instances</span>
                                  </div>
                                </td>
                                <td className="py-3 px-4">
                                  <span className="font-bold">{resourceData.ec2.total}</span>
                                </td>
                                <td className="py-3 px-4">
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded">
                                      {resourceData.ec2.running} running
                                    </span>
                                    <span className="text-xs px-2 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded">
                                      {resourceData.ec2.stopped} stopped
                                    </span>
                                  </div>
                                </td>
                                <td className="py-3 px-4">
                                  <span className="text-sm text-muted-foreground">
                                    Avg {resourceData.ec2.avg_running_hours?.toFixed(1)} hours running
                                  </span>
                                </td>
                              </tr>
                            )}

                            {resourceData.s3?.total_buckets > 0 && (
                              <tr className="border-b border-border hover:bg-muted/50">
                                <td className="py-3 px-4">
                                  <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center">
                                      <HardDrive className="w-4 h-4 text-blue-600" />
                                    </div>
                                    <span className="font-medium">S3 Buckets</span>
                                  </div>
                                </td>
                                <td className="py-3 px-4">
                                  <span className="font-bold">{resourceData.s3.total_buckets}</span>
                                </td>
                                <td className="py-3 px-4">
                                  <div className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
                                    Storage
                                  </div>
                                </td>
                                <td className="py-3 px-4">
                                  <span className="text-sm text-muted-foreground">
                                    Avg age: {resourceData.s3.avg_age_days?.toFixed(1)} days
                                  </span>
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </>
                  ) : (
                    <div className="text-center py-12">
                      <Database className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-50" />
                      <h4 className="text-lg font-semibold text-foreground mb-2">No Resource Summary Data</h4>
                      <p className="text-muted-foreground mb-6">
                        Resource summary data is not available. Try refreshing or check permissions.
                      </p>
                      <button onClick={() => fetchResourceData(true)} className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:opacity-90">
                        Load Resource Summary
                      </button>
                    </div>
                  )}
                </Card>
              </div>
            )}

            {/* Overview Cards - YOUR EXISTING CODE (UNCHANGED) */}
            {selectedMenu === "overview" && accountId && (
              <>
                <div className="grid grid-cols-3 gap-4">
                  <Card>
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground mb-1">Total AWS Spend (Last 90 Days)</p>
                        <p className="text-2xl font-bold text-foreground">
                          ${providerData.total_spend.toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                          })}
                        </p>
                      </div>
                      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                        <DollarSign className="w-5 h-5 text-primary" />
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-4">
                      {providerData.monthly_change > 0 ? (
                        <>
                          <TrendingUp className="w-4 h-4 text-error" />
                          <span className="text-sm text-error">
                            +{Math.min(providerData.monthly_change, 1000).toFixed(1)}% vs last month
                          </span>
                        </>
                      ) : (
                        <>
                          <TrendingDown className="w-4 h-4 text-success" />
                          <span className="text-sm text-success">
                            {providerData.monthly_change.toFixed(1)}% vs last month
                          </span>
                        </>
                      )}
                    </div>
                  </Card>
                  
                  <Card>
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground mb-1">Yesterday's Spend</p>
                        <p className="text-3xl font-bold text-foreground">
                          ${providerData.today_spend.toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                          })}
                        </p>
                      </div>
                      <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
                        <Calendar className="w-5 h-5 text-accent-foreground" />
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground mt-4">
                      {getYesterday()} • AWS bills with 1-day delay
                    </p>
                  </Card>

                  <Card>
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground mb-1">This Month ({providerData.current_month_name || 'Current'})</p>
                        <p className="text-2xl font-bold text-foreground">
                          ${providerData.current_month_spend.toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                          })}
                        </p>
                      </div>
                      <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center">
                        <TrendingUp className="w-5 h-5 text-warning" />
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground mt-4">
                      Month-to-date total • Forecast: ${providerData.forecast.thirtyDay.toFixed(2)}
                    </p>
                  </Card>
                </div>

                <Card className="p-6">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold text-foreground">Last 7 Days Spend</h3>
                    {providerData.daily_spend.length > 0 && (
                      <span className="text-sm text-muted-foreground">
                        Daily actual spends (AWS reports with 1-day delay)
                      </span>
                    )}
                  </div>
                  
                  {providerData.daily_spend.length > 0 ? (
                    <div className="space-y-4">
                      <div className="relative h-64">
                        <div className="absolute left-0 top-0 bottom-0 w-10 flex flex-col justify-between text-xs text-muted-foreground py-8">
                          {(() => {
                            const amounts = providerData.daily_spend.map(d => d.amount);
                            const maxAmount = Math.max(...amounts, 1);
                            const steps = [1, 0.75, 0.5, 0.25, 0];
                            return steps.map((step, i) => (
                              <div key={i} className="flex items-center">
                                <span className="mr-1 text-[10px]">${(maxAmount * step).toFixed(2)}</span>
                                <div className="flex-1 border-t border-border/30"></div>
                              </div>
                            ));
                          })()}
                        </div>
                        
                        <div className="ml-10 h-full">
                          <div className="h-full flex items-end justify-between gap-2 px-2">
                            {providerData.daily_spend.map((day, i) => {
                              const amounts = providerData.daily_spend.map(d => d.amount);
                              const maxAmount = Math.max(...amounts, 1);
                              const heightPercentage = day.amount === 0 ? 5 : Math.max((day.amount / maxAmount) * 90, 5);
                              
                              const getBarColor = (amount: number) => {
                                if (amount === 0) return 'bg-gray-300 dark:bg-gray-700';
                                if (amount < maxAmount * 0.25) return 'bg-gradient-to-t from-green-500 to-green-400 hover:from-green-600 hover:to-green-500';
                                if (amount < maxAmount * 0.5) return 'bg-gradient-to-t from-blue-500 to-blue-400 hover:from-blue-600 hover:to-blue-500';
                                if (amount < maxAmount * 0.75) return 'bg-gradient-to-t from-yellow-500 to-yellow-400 hover:from-yellow-600 hover:to-yellow-500';
                                return 'bg-gradient-to-t from-red-500 to-red-400 hover:from-red-600 hover:to-red-500';
                              };
                              
                              return (
                                <div key={i} className="flex-1 flex flex-col items-center justify-end group h-full">
                                  <div className="relative flex flex-col items-center w-full">
                                    <div className="mb-1 text-xs font-semibold text-foreground/90 bg-card/50 px-1 py-0.5 rounded">
                                      ${day.amount.toFixed(2)}
                                    </div>
                                    <div className="w-full flex items-end" style={{ height: 'calc(100% - 2rem)' }}>
                                      <div
                                        className={`relative w-3/4 mx-auto rounded-t-lg transition-all duration-300 ${getBarColor(day.amount)} 
                                          group-hover:w-5/6 group-hover:shadow-lg group-hover:scale-105`}
                                        style={{ height: `${heightPercentage}%`, minHeight: '20px' }}
                                      >
                                        <div className="absolute inset-x-0 top-0 h-1/3 rounded-t-lg bg-white/30"></div>
                                        <div className="absolute -top-16 left-1/2 -translate-x-1/2 bg-card border border-border px-3 py-2 rounded-lg text-sm opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10 shadow-xl pointer-events-none">
                                          <div className="font-semibold text-foreground">
                                            {day.day_name || day.date}
                                          </div>
                                          <div className="text-primary font-bold text-lg">
                                            ${day.amount.toLocaleString(undefined, {
                                              minimumFractionDigits: 2,
                                              maximumFractionDigits: 2
                                            })}
                                          </div>
                                          {day.full_date && (
                                            <div className="text-xs text-muted-foreground mt-1">
                                              {day.full_date}
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                  <div className="mt-2 w-full text-center pt-2 border-t border-border/30">
                                    <div className="text-sm font-semibold text-foreground">{day.date}</div>
                                    {day.day_name && (
                                      <div className="text-xs text-muted-foreground capitalize">{day.day_name}</div>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                          <div className="absolute left-0 right-0 bottom-12 border-t-2 border-border"></div>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                        <div className="flex items-center gap-2 p-3 bg-card/30 rounded-lg border border-border/20">
                          <div className="w-3 h-3 rounded-full bg-green-500"></div>
                          <div>
                            <div className="text-xs text-muted-foreground">Lowest</div>
                            <div className="font-semibold text-foreground">
                              ${Math.min(...providerData.daily_spend.map(d => d.amount)).toFixed(2)}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 p-3 bg-card/30 rounded-lg border border-border/20">
                          <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                          <div>
                            <div className="text-xs text-muted-foreground">Average</div>
                            <div className="font-semibold text-foreground">
                              ${(providerData.daily_spend.reduce((sum, day) => sum + day.amount, 0) / providerData.daily_spend.length).toFixed(2)}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 p-3 bg-card/30 rounded-lg border border-border/20">
                          <div className="w-3 h-3 rounded-full bg-red-500"></div>
                          <div>
                            <div className="text-xs text-muted-foreground">Highest</div>
                            <div className="font-semibold text-foreground">
                              ${Math.max(...providerData.daily_spend.map(d => d.amount)).toFixed(2)}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 p-3 bg-card/30 rounded-lg border border-border/20">
                          <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                          <div>
                            <div className="text-xs text-muted-foreground">7-Day Total</div>
                            <div className="font-semibold text-foreground">
                              ${providerData.daily_spend.reduce((sum, day) => sum + day.amount, 0).toFixed(2)}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="h-64 flex flex-col items-center justify-center text-muted-foreground p-8">
                      {loading ? (
                        <div className="text-center">
                          <Loader2 className="w-10 h-10 animate-spin mb-3 mx-auto text-primary" />
                          <p className="text-foreground/80">Loading daily spend data...</p>
                          <p className="text-sm text-muted-foreground mt-1">Fetching from AWS Cost Explorer</p>
                        </div>
                      ) : (
                        <>
                          <div className="relative mb-6">
                            <div className="w-20 h-20 bg-gradient-to-br from-primary/10 to-primary/5 rounded-full flex items-center justify-center">
                              <DollarSign className="w-10 h-10 text-primary/40" />
                            </div>
                            <div className="absolute inset-0 border-2 border-dashed border-primary/20 rounded-full animate-pulse"></div>
                          </div>
                          <h4 className="text-lg font-semibold text-foreground mb-2">No Daily Data Available</h4>
                          <p className="text-muted-foreground text-center mb-6 max-w-md">
                            Connect and sync your AWS account to see daily cost trends visualized in the bar chart
                          </p>
                          <div className="flex gap-3">
                            <button onClick={() => setSelectedMenu("connect")} className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition font-medium">
                              Connect Account
                            </button>
                            {accountId && (
                              <button onClick={refreshAnalytics} className="px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:opacity-90 transition font-medium">
                                <RefreshCw className="w-4 h-4 inline mr-2" />
                                Sync Data
                              </button>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </Card>

                {selectedAccount?.last_synced && (
                  <div className="text-sm text-muted-foreground text-center">
                    Last synced: {new Date(selectedAccount.last_synced).toLocaleString()}
                  </div>
                )}
              </>
            )}

            {/* Connect Account Section - YOUR EXISTING CODE (UNCHANGED) */}
            {selectedMenu === "connect" && (
              <Card className="p-6">
                <h3 className="text-2xl font-bold text-foreground mb-2">
                  Connect Your AWS Account
                </h3>
                <p className="text-muted-foreground mb-6">
                  Securely connect your AWS account to monitor cost and resources
                </p>

                {awsAccounts.length > 0 && (
                  <div className="mb-6 p-4 bg-success/10 border border-success/20 rounded-lg">
                    <div className="flex items-center gap-2 text-success">
                      <CheckCircle className="w-5 h-5" />
                      <span className="font-medium">
                        {awsAccounts.length} AWS account(s) already connected
                      </span>
                    </div>
                    <p className="text-sm text-success/80 mt-1">
                      Switch to "Overview" tab to view cost analytics
                    </p>
                  </div>
                )}

                <div className="space-y-6 mb-8">
                  {manualInstructions.steps.map((step, index) => (
                    <div key={index} className="border-l-4 border-blue-500 pl-4">
                      <div className="flex items-start gap-3 mb-3">
                        <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center flex-shrink-0">
                          <span className="font-semibold text-blue-700 dark:text-blue-300">
                            {index + 1}
                          </span>
                        </div>
                        <h4 className="font-semibold text-lg text-foreground">{step.title}</h4>
                      </div>
                      <ul className="space-y-2 ml-11">
                        {step.instructions.map((instruction, i) => {
                          let displayInstruction = instruction
                          if (instruction.includes("026395503692")) {
                            displayInstruction = instruction.replace(
                              "026395503692",
                              `<span class="font-bold text-blue-600">${awsInfo?.platform_account_id || "026395503692"}</span>`
                            )
                          }
                          if (instruction.includes("CloudCostReadOnlyRole")) {
                            displayInstruction = instruction.replace(
                              "CloudCostReadOnlyRole",
                              `<span class="font-bold text-blue-600">${awsInfo?.role_name || "CloudCostReadOnlyRole"}</span>`
                            )
                          }
                          
                          return (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-blue-500 mt-1">•</span>
                              <span 
                                className="text-muted-foreground"
                                dangerouslySetInnerHTML={{ __html: displayInstruction }}
                              />
                            </li>
                          )
                        })}
                      </ul>
                    </div>
                  ))}
                </div>

                {awsInfo && (
                  <div className="mb-6 p-4 bg-muted rounded-lg">
                    <h4 className="font-semibold text-foreground mb-3">Required Information</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Platform AWS Account ID:</span>
                        <code className="font-mono font-bold text-foreground">
                          {awsInfo.platform_account_id}
                        </code>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Role Name:</span>
                        <code className="font-mono font-bold text-foreground">
                          {awsInfo.role_name}
                        </code>
                      </div>
                      <div className="mt-3 pt-3 border-t border-border">
                        <span className="text-muted-foreground">Permissions included:</span>
                        <p className="text-sm text-foreground mt-1">
                          Read-only billing, compute, storage, IAM metadata, and cost explorer access
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="mb-6">
                  <button
                    onClick={createRoleInAws}
                    disabled={awsLoading}
                    className="w-full h-12 px-6 bg-primary text-primary-foreground rounded-lg font-medium hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {awsLoading ? (
                      <span className="flex items-center justify-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Generating External ID...
                      </span>
                    ) : (
                      "Step 1: Generate External ID"
                    )}
                  </button>
                </div>

                {externalId && (
                  <div className="mb-8 space-y-6">
                    <div>
                      <h4 className="font-semibold text-foreground mb-3">Step 2: Copy External ID</h4>
                      <div className="relative">
                        <code className="block p-4 bg-muted rounded-lg text-sm font-mono break-all">
                          {externalId}
                        </code>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(externalId)
                            setStatus("External ID copied to clipboard!")
                            setIsConnectionSuccess(true)
                            setTimeout(() => setStatus(null), 2000)
                          }}
                          className="absolute top-2 right-2 px-3 py-1 text-xs bg-primary text-primary-foreground rounded hover:opacity-90 transition"
                        >
                          Copy
                        </button>
                      </div>
                      <p className="text-sm text-muted-foreground mt-2">
                        This External ID is required when creating the IAM role in AWS
                      </p>
                    </div>

                    <div>
                      <h4 className="font-semibold text-foreground mb-3">Step 3: Copy Policy JSON</h4>
                      <div className="relative">
                        <pre className="p-4 bg-muted rounded-lg text-xs font-mono overflow-auto max-h-60">
                          {policyJson}
                        </pre>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(policyJson)
                            setStatus("Policy JSON copied to clipboard!")
                            setIsConnectionSuccess(true)
                            setTimeout(() => setStatus(null), 2000)
                          }}
                          className="absolute top-2 right-2 px-3 py-1 text-xs bg-primary text-primary-foreground rounded hover:opacity-90 transition"
                        >
                          Copy
                        </button>
                      </div>
                    </div>

                    <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                      <h4 className="font-semibold text-blue-700 dark:text-blue-300 mb-2">
                        Important Notes
                      </h4>
                      <ul className="space-y-1 text-sm text-blue-600 dark:text-blue-400">
                        <li>• Complete all 4 steps in the AWS Console before proceeding</li>
                        <li>• The External ID ensures secure cross-account access</li>
                        <li>• The policy provides read-only access only</li>
                        <li>• After creating the role, AWS will provide a Role ARN</li>
                      </ul>
                    </div>
                  </div>
                )}

                <div>
                  <h4 className="font-semibold text-foreground mb-3">
                    Step 4: Enter Role ARN
                  </h4>
                  <div className="space-y-4">
                    <input
                      value={roleArn}
                      onChange={(e) => setRoleArn(e.target.value)}
                      placeholder="arn:aws:iam::123456789012:role/CloudCostReadOnlyRole"
                      className="w-full px-4 py-3 bg-input border border-border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                      disabled={!externalId}
                    />
                    <button
                      onClick={connectAccount}
                      disabled={awsLoading || !roleArn.trim()}
                      className="w-full h-12 px-6 bg-green-600 text-white rounded-lg font-medium hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {awsLoading ? (
                        <span className="flex items-center justify-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Connecting...
                        </span>
                      ) : (
                        "Connect AWS Account"
                      )}
                    </button>
                  </div>
                  <p className="text-sm text-muted-foreground mt-3">
                    Paste the Role ARN exactly as shown in AWS IAM Console
                  </p>
                </div>

                <div className="mt-8 pt-6 border-t border-border">
                  <h4 className="font-semibold text-foreground mb-3">Need Help?</h4>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    <li>• Ensure you have IAM permissions to create roles in your AWS account</li>
                    <li>• Verify the External ID matches exactly</li>
                    <li>• Check that the trust relationship includes Account ID: {awsInfo?.platform_account_id || "026395503692"}</li>
                    <li>• Make sure the role name is exactly "CloudCostReadOnlyRole"</li>
                  </ul>
                </div>
              </Card>
            )}

            {/* Placeholder for other sections - YOUR EXISTING CODE (UNCHANGED) */}
            {!["overview", "connect", "services", "resources"].includes(selectedMenu) && (
              <Card>
                <div className="text-center py-12">
                  <Settings className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    {menuItems.find((m) => m.id === selectedMenu)?.label}
                  </h3>
                  <p className="text-muted-foreground">This feature is coming soon</p>
                  <p className="text-sm text-muted-foreground mt-2">
                    Connect your AWS account to access detailed cost analytics
                  </p>
                </div>
              </Card>
            )}

            {/* No Account Selected - YOUR EXISTING CODE (UNCHANGED) */}
            {selectedMenu === "overview" && !accountId && awsAccounts.length === 0 && (
              <Card>
                <div className="text-center py-12">
                  <Settings className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    No AWS Account Connected
                  </h3>
                  <p className="text-muted-foreground mb-6">
                    Connect an AWS account to view cost analytics and insights
                  </p>
                  <button
                    onClick={() => setSelectedMenu("connect")}
                    className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:opacity-90 transition"
                  >
                    Connect AWS Account
                  </button>
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}

// ============================================
// LOW-LEVEL SERVICES COMPONENT - FIXED
// ============================================
const LowLevelServicesComponent: React.FC<{ accountId: number | null }> = ({ accountId: propAccountId }) => {
  // State
  const [data, setData] = useState<LowLevelServicesData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    search: '',
    categories: [] as string[],
    regions: [] as string[],
    minCost: 0,
    maxCost: Infinity
  });
  const [selectedService, setSelectedService] = useState<LowLevelServiceCategoryData | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [localAccountId, setLocalAccountId] = useState<number | null>(propAccountId);
  const [accounts, setAccounts] = useState<AWSAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(propAccountId);
  const [initialFetchDone, setInitialFetchDone] = useState(false);

  // Auth helper
  const getAuthToken = () => {
    return localStorage.getItem('token') || sessionStorage.getItem('token');
  };

  // Fetch available AWS accounts
  const fetchAccounts = async () => {
    try {
      const token = getAuthToken();
      if (!token) throw new Error('No authentication token');

      const response = await fetch('http://localhost:8000/aws-accounts/', {
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) throw new Error('Failed to fetch accounts');
      
      const data = await response.json();
      setAccounts(data || []);
      
      // Auto-select first account if none selected
      if (data?.length > 0 && !selectedAccountId && !propAccountId) {
        setSelectedAccountId(data[0].id);
        setLocalAccountId(data[0].id);
      }
    } catch (err) {
      console.error('Error fetching accounts:', err);
    }
  };

  // Fetch services
  const fetchServices = async (accountIdToUse: number) => {
    if (!accountIdToUse) {
      console.error('No account ID provided');
      setError('No AWS account selected');
      return;
    }
    
    setLoading(true);
    setError(null);
    setData(null); // Clear previous data
    
    try {
      const token = getAuthToken();
      if (!token) throw new Error('No authentication token');

      console.log('Fetching low-level services for account ID:', accountIdToUse);
      
      // FIXED: Changed URL to match Django endpoint
      const response = await fetch(
        `http://localhost:8000/api/aws/accounts/${accountIdToUse}/low-level-services/`,
        { 
          headers: { 
            'Authorization': `Token ${token}`, 
            'Content-Type': 'application/json' 
          } 
        }
      );

      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error(`Failed to fetch low-level services: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('Received data:', result);
      
      // Validate the response structure
      if (!result || typeof result !== 'object') {
        throw new Error('Invalid response format');
      }
      
      setData(result);
      setInitialFetchDone(true);
      
      // Auto-expand top 3 categories by cost
      if (result.services_by_category) {
        try {
          const entries = Object.entries(result.services_by_category);
          const validEntries = entries.filter(([_, a]) => {
            const category = a as LowLevelServiceCategoryData;
            return category && typeof category.total_monthly_cost === 'number' && !isNaN(category.total_monthly_cost);
          });
          
          const topCategories = validEntries
            .sort(([, a], [, b]) => {
              const categoryA = a as LowLevelServiceCategoryData;
              const categoryB = b as LowLevelServiceCategoryData;
              return (categoryB.total_monthly_cost || 0) - (categoryA.total_monthly_cost || 0);
            })
            .slice(0, 3)
            .map(([id]) => id);
          
          setExpandedCategories(new Set(topCategories));
        } catch (err) {
          console.error('Error auto-expanding categories:', err);
        }
      }
    } catch (err) {
      console.error('Error fetching services:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch services');
    } finally {
      setLoading(false);
    }
  };

  // Load accounts on mount
  useEffect(() => {
    fetchAccounts();
  }, []);

  // Use prop accountId if provided, otherwise use selected account
useEffect(() => {
  if (propAccountId) {
    setLocalAccountId(propAccountId);
    setSelectedAccountId(propAccountId);
    fetchServices(propAccountId);
  }
}, [propAccountId]); // Only depend on propAccountId

// Fetch services when selected account changes
useEffect(() => {
  if (selectedAccountId && !propAccountId && !initialFetchDone) {
    setLocalAccountId(selectedAccountId);
    fetchServices(selectedAccountId);
    setInitialFetchDone(true);
  }
}, [selectedAccountId, propAccountId]);
  // Handlers
  const handleAccountChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = parseInt(e.target.value);
    setSelectedAccountId(id);
    setInitialFetchDone(false);
  };

  const toggleCategory = (categoryId: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  };

  const expandAll = () => {
    if (data?.services_by_category) {
      try {
        setExpandedCategories(new Set(Object.keys(data.services_by_category)));
      } catch (err) {
        console.error('Error expanding all categories:', err);
      }
    }
  };

  const collapseAll = () => {
    setExpandedCategories(new Set());
  };

  // Filters
  const filteredCategories = () => {
    if (!data?.services_by_category) return [];
    
    try {
      const entries = Object.entries(data.services_by_category);
      
      return entries
        .filter(([_, category]) => {
          const cat = category as LowLevelServiceCategoryData;
          
          if (filters.search) {
            const searchLower = filters.search.toLowerCase();
            const matches = 
              (cat.service_info?.name?.toLowerCase() || '').includes(searchLower) ||
              (cat.service_info?.description?.toLowerCase() || '').includes(searchLower) ||
              (cat.category?.toLowerCase() || '').includes(searchLower) ||
              (cat.resources || []).some(r => 
                (r?.resource_name?.toLowerCase() || '').includes(searchLower) ||
                (r?.resource_id?.toLowerCase() || '').includes(searchLower)
              );
            if (!matches) return false;
          }
          
          if (filters.categories.length > 0 && !filters.categories.includes(cat.category)) return false;
          
          if (filters.regions.length > 0) {
            const hasRegion = (cat.resources || []).some(r => 
              r?.region && filters.regions.includes(r.region)
            );
            if (!hasRegion) return false;
          }
          
          const monthlyCost = cat.total_monthly_cost || 0;
          if (monthlyCost < filters.minCost) return false;
          if (monthlyCost > filters.maxCost) return false;
          
          return true;
        })
        .sort(([, a], [, b]) => {
          const catA = a as LowLevelServiceCategoryData;
          const catB = b as LowLevelServiceCategoryData;
          return (catB.total_monthly_cost || 0) - (catA.total_monthly_cost || 0);
        });
    } catch (error) {
      console.error('Error filtering categories:', error);
      return [];
    }
  };
  
  // Safe access for allCategories
  const allCategories = React.useMemo(() => {
    if (!data?.services_by_category) return [];
    
    try {
      const categories = Object.values(data.services_by_category)
        .map(s => {
          const cat = s as LowLevelServiceCategoryData;
          return cat?.category;
        })
        .filter((cat): cat is string => Boolean(cat));
      
      return [...new Set(categories)];
    } catch (err) {
      console.error('Error getting allCategories:', err);
      return [];
    }
  }, [data?.services_by_category]);
  
  // Safe access for allRegions
  const allRegions = React.useMemo(() => {
    if (!data?.all_resources) return [];
    
    try {
      const regions = data.all_resources
        .map(r => r?.region)
        .filter((region): region is string => Boolean(region));
      
      return [...new Set(regions)];
    } catch (err) {
      console.error('Error getting allRegions:', err);
      return [];
    }
  }, [data?.all_resources]);

  // Safe access for summary values
  const totalMonthlyCost = React.useMemo(() => {
    return typeof data?.summary?.estimated_monthly_cost === 'number' && !isNaN(data.summary.estimated_monthly_cost)
      ? data.summary.estimated_monthly_cost
      : 0;
  }, [data?.summary?.estimated_monthly_cost]);
  
  const totalResources = data?.summary?.total_services ?? 0;
  const uniqueServices = data?.summary?.unique_services_discovered ?? 0;

  // Safe auto-expand in useEffect
  useEffect(() => {
    if (data?.services_by_category && !initialFetchDone) {
      try {
        const entries = Object.entries(data.services_by_category);
        const validEntries = entries.filter(([_, a]) => {
          const cat = a as LowLevelServiceCategoryData;
          return cat && typeof cat.total_monthly_cost === 'number' && !isNaN(cat.total_monthly_cost);
        });
        
        const topCategories = validEntries
          .sort(([, a], [, b]) => {
            const catA = a as LowLevelServiceCategoryData;
            const catB = b as LowLevelServiceCategoryData;
            return (catB.total_monthly_cost || 0) - (catA.total_monthly_cost || 0);
          })
          .slice(0, 3)
          .map(([id]) => id);
        
        setExpandedCategories(new Set(topCategories));
      } catch (error) {
        console.error('Error auto-expanding categories:', error);
      }
    }
  }, [data, initialFetchDone]);

  // Service Icon Component
  const ServiceIcon = ({ category, className = "w-5 h-5" }: { category: string; className?: string }) => {
    const iconMap: Record<string, React.ReactNode> = {
      'Virtual Private Cloud': <Network className={className} />,
      'Elastic Compute Cloud': <Cpu className={className} />,
      'Simple Storage Service': <HardDrive className={className} />,
      'Relational Database Service': <Database className={className} />,
      'DynamoDB': <Database className={className} />,
      'Lambda': <Cloud className={className} />,
      'Route 53': <Globe className={className} />,
      'CloudFront': <Cloud className={className} />,
      'API Gateway': <Settings className={className} />,
      'Elastic Load Balancing': <Server className={className} />,
      'Identity & Access Management': <Shield className={className} />,
    };
    return iconMap[category] || <Box className={className} />;
  };

  // Pricing Badges Component
  const PricingBadges = ({ service }: { service: LowLevelService }) => {
    if (!service) return null;
    
    const items = [];
    if (service.price_per_hour) items.push(`$${service.price_per_hour}/hour`);
    if (service.price_per_gb_month) items.push(`$${service.price_per_gb_month}/GB-month`);
    if (service.price_per_million) items.push(`$${service.price_per_million}/million`);
    if (service.price_per_gb) items.push(`$${service.price_per_gb}/GB`);
    if (service.price_per_vcpu_hour) items.push(`$${service.price_per_vcpu_hour}/vCPU-hour`);
    if (service.price_per_month) items.push(`$${service.price_per_month}/month`);
    
    if (items.length === 0) return null;
    
    return (
      <div className="flex flex-wrap gap-2">
        {items.slice(0, 3).map((item, idx) => (
          <span key={idx} className="text-xs px-2 py-1 bg-primary/10 text-primary rounded">
            {item}
          </span>
        ))}
        {items.length > 3 && (
          <span className="text-xs px-2 py-1 bg-muted text-muted-foreground rounded">
            +{items.length - 3} more
          </span>
        )}
      </div>
    );
  };

  // Loading state
  if (loading && !data) {
    return (
      <Card className="p-6">
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 className="w-12 h-12 animate-spin text-primary mb-4" />
          <p className="text-lg font-medium text-foreground">Discovering Low-Level Services...</p>
          <p className="text-sm text-muted-foreground mt-2">
            This may take a minute while we scan multiple regions
          </p>
        </div>
      </Card>
    );
  }

  // No account ID and accounts are loading
  if (!localAccountId && accounts.length === 0) {
    return (
      <Card className="p-6">
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 className="w-12 h-12 animate-spin text-primary mb-4" />
          <p className="text-lg font-medium text-foreground">Loading AWS accounts...</p>
        </div>
      </Card>
    );
  }

  // No account ID but accounts are loaded
  if (!localAccountId && accounts.length > 0) {
    return (
      <Card className="p-6">
        <div className="text-center py-12">
          <AlertTriangle className="w-12 h-12 text-orange-500 mx-auto mb-4" />
          <h4 className="text-lg font-semibold text-foreground mb-2">No AWS Account Selected</h4>
          <p className="text-muted-foreground mb-6">Please select an AWS account to view low-level services</p>
          <div className="max-w-xs mx-auto">
            <label htmlFor="ll-account-select" className="block text-sm font-medium text-muted-foreground mb-2">
              Select AWS Account
            </label>
            <select
              id="ll-account-select"
              title="Select AWS Account for Low-Level Services"
              value={selectedAccountId || ''}
              onChange={handleAccountChange}
              className="w-full px-4 py-2 bg-card border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              <option value="">Select an account...</option>
              {accounts.map(account => (
                <option key={account.id} value={account.id}>
                  {account.account_name} ({account.account_id})
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>
    );
  }

  const filteredCats = filteredCategories();

  return (
    <Card className="p-6">
      {/* Header with Account Selector */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-2xl font-bold text-foreground">Low-Level Services</h3>
          <p className="text-muted-foreground">
            Detailed tracking of AWS low-level services with granular pricing and resource-level visibility
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Account Selector - Only show if no prop accountId */}
          {!propAccountId && accounts.length > 0 && (
            <select
              id="ll-account-select-header"
              title="Select AWS Account for Low-Level Services"
              value={selectedAccountId || ''}
              onChange={handleAccountChange}
              className="px-3 py-2 bg-card border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              {accounts.map(account => (
                <option key={account.id} value={account.id}>
                  {account.account_name}
                </option>
              ))}
            </select>
          )}
          
          <button 
            onClick={expandAll} 
            disabled={!data?.services_by_category}
            className="px-3 py-2 text-sm border border-border rounded-lg hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
            title="Expand all categories"
          >
            Expand All
          </button>
          <button 
            onClick={collapseAll} 
            className="px-3 py-2 text-sm border border-border rounded-lg hover:bg-muted"
            title="Collapse all categories"
          >
            Collapse All
          </button>
          <button 
            onClick={() => localAccountId && fetchServices(localAccountId)} 
            disabled={loading || !localAccountId} 
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Refresh
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="mb-6 space-y-4">
        <div className="flex items-center gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              placeholder="Search services, resources, or categories..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              className="w-full px-4 py-2 pl-10 bg-card border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-2 border border-border rounded-lg hover:bg-muted transition-colors ${
              showFilters ? 'bg-primary/10 border-primary' : ''
            }`}
            title="Filter"
          >
            <Filter className="w-5 h-5" />
          </button>
        </div>

        {showFilters && (
          <Card className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label htmlFor="category-filter" className="text-xs font-medium mb-1 block">Categories</label>
                <select
                  id="category-filter"
                  title="Filter by category"
                  multiple
                  value={filters.categories}
                  onChange={(e) => setFilters({ 
                    ...filters, 
                    categories: Array.from(e.target.selectedOptions, o => o.value) 
                  })}
                  className="w-full px-3 py-2 bg-card border border-border rounded-lg text-sm"
                  size={4}
                >
                  {allCategories.map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="region-filter" className="text-xs font-medium mb-1 block">Regions</label>
                <select
                  id="region-filter"
                  title="Filter by region"
                  multiple
                  value={filters.regions}
                  onChange={(e) => setFilters({ 
                    ...filters, 
                    regions: Array.from(e.target.selectedOptions, o => o.value) 
                  })}
                  className="w-full px-3 py-2 bg-card border border-border rounded-lg text-sm"
                  size={4}
                >
                  {allRegions.map(region => (
                    <option key={region} value={region}>{region}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="min-cost" className="text-xs font-medium mb-1 block">Min Cost ($)</label>
                <input
                  id="min-cost"
                  type="number"
                  min="0"
                  step="0.01"
                  value={filters.minCost || ''}
                  onChange={(e) => setFilters({ ...filters, minCost: Math.max(0, Number(e.target.value) || 0) })}
                  className="w-full px-3 py-2 bg-card border border-border rounded-lg text-sm"
                  placeholder="0"
                />
              </div>
              <div>
                <label htmlFor="max-cost" className="text-xs font-medium mb-1 block">Max Cost ($)</label>
                <input
                  id="max-cost"
                  type="number"
                  min="0"
                  step="0.01"
                  value={filters.maxCost === Infinity ? '' : filters.maxCost}
                  onChange={(e) => setFilters({ 
                    ...filters, 
                    maxCost: e.target.value ? Number(e.target.value) : Infinity 
                  })}
                  className="w-full px-3 py-2 bg-card border border-border rounded-lg text-sm"
                  placeholder="No limit"
                />
              </div>
            </div>
            <div className="flex justify-end mt-4">
              <button
                onClick={() => setFilters({
                  search: '',
                  categories: [],
                  regions: [],
                  minCost: 0,
                  maxCost: Infinity
                })}
                className="text-sm text-primary hover:underline"
              >
                Clear all filters
              </button>
            </div>
          </Card>
        )}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Monthly Cost</p>
              <p className="text-2xl font-bold text-foreground">
                ${typeof totalMonthlyCost === 'number' && !isNaN(totalMonthlyCost)
                  ? totalMonthlyCost.toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2
                    })
                  : '0.00'}
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/20 flex items-center justify-center">
              <Layers className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total Resources</p>
              <p className="text-2xl font-bold text-foreground">{totalResources}</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/20 flex items-center justify-center">
              <Box className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Unique Services</p>
              <p className="text-2xl font-bold text-foreground">{uniqueServices}</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-orange-100 dark:bg-orange-900/20 flex items-center justify-center">
              <Globe className="w-5 h-5 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Regions</p>
              <p className="text-2xl font-bold text-foreground">{allRegions.length}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {allRegions.slice(0, 3).join(', ')}
                {allRegions.length > 3 ? '...' : ''}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Content */}
      {error ? (
        <div className="text-center py-12">
          <AlertTriangle className="w-12 h-12 text-orange-500 mx-auto mb-4" />
          <h4 className="text-lg font-semibold text-foreground mb-2">Unable to Load Services</h4>
          <p className="text-muted-foreground mb-6">{error}</p>
          <button
            onClick={() => localAccountId && fetchServices(localAccountId)}
            className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:opacity-90"
          >
            Retry
          </button>
        </div>
      ) : filteredCats.length > 0 ? (
        <div className="space-y-4">
          {filteredCats.map(([serviceId, categoryData]) => {
            const cat = categoryData as LowLevelServiceCategoryData;
            if (!cat || !cat.service_info) return null;
            
            return (
              <Card key={serviceId} className="p-4 hover:shadow-md transition-shadow">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <ServiceIcon category={cat.category || ''} className="w-5 h-5 text-primary" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="text-lg font-semibold text-foreground">
                          {cat.service_info.name || 'Unknown Service'}
                        </h4>
                        <span className="text-xs px-2 py-1 bg-primary/10 text-primary rounded-full">
                          {cat.category || 'Uncategorized'}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">
                        {cat.service_info.description || 'No description available'}
                      </p>
                      <PricingBadges service={cat.service_info} />
                    </div>
                  </div>
                  <div className="text-right ml-4">
                    <p className="text-2xl font-bold text-foreground">
                      ${typeof cat.total_monthly_cost === 'number' && !isNaN(cat.total_monthly_cost)
                        ? cat.total_monthly_cost.toFixed(2)
                        : '0.00'}
                    </p>
                    <p className="text-xs text-muted-foreground">per month</p>
                    <div className="flex items-center justify-end gap-2 mt-2">
                      <span className="text-xs text-muted-foreground">
                        {cat.total_count || 0} resources
                      </span>
                      <button
                        onClick={() => toggleCategory(serviceId)}
                        className="p-1 hover:bg-muted rounded"
                        title={expandedCategories.has(serviceId) ? "Collapse" : "Expand"}
                      >
                        {expandedCategories.has(serviceId) ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Expanded Resources */}
                {expandedCategories.has(serviceId) && (
                  <div className="mt-4 pt-4 border-t border-border">
                    <div className="flex justify-between items-center mb-3">
                      <h5 className="font-medium text-foreground">
                        Resources ({cat.resources?.length || 0})
                      </h5>
                      <button
                        onClick={() => {
                          setSelectedService(cat);
                          setModalOpen(true);
                        }}
                        className="text-xs text-primary hover:underline"
                      >
                        View All
                      </button>
                    </div>
                    
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {(cat.resources || [])
                        .filter(r => r && typeof r.estimated_monthly_cost === 'number' && !isNaN(r.estimated_monthly_cost))
                        .sort((a, b) => (b.estimated_monthly_cost || 0) - (a.estimated_monthly_cost || 0))
                        .slice(0, 5)
                        .map((resource, idx) => (
                          <div key={idx} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <p className="font-medium text-sm text-foreground">
                                  {resource.resource_name || 'Unnamed Resource'}
                                </p>
                                <span className="text-xs px-2 py-0.5 bg-card rounded-full">
                                  {resource.region || 'Unknown'}
                                </span>
                              </div>
                              <p className="text-xs text-muted-foreground mt-1 font-mono">
                                {resource.resource_id || 'No ID'}
                              </p>
                            </div>
                            <div className="text-right ml-4">
                              <p className="text-lg font-semibold text-foreground">
                                ${(resource.estimated_monthly_cost || 0).toFixed(2)}
                              </p>
                              <p className="text-xs text-muted-foreground">monthly</p>
                            </div>
                          </div>
                        ))}
                      
                      {cat.resources && cat.resources.length > 5 && (
                        <div className="text-center pt-2">
                          <p className="text-sm text-muted-foreground">
                            + {cat.resources.length - 5} more resources
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-12">
          <Box className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-50" />
          <h4 className="text-lg font-semibold text-foreground mb-2">No Services Found</h4>
          <p className="text-muted-foreground">
            {filters.search || filters.categories.length > 0 || filters.regions.length > 0
              ? 'Try adjusting your filters'
              : data ? 'No low-level services discovered in this account' : 'Click Refresh to discover services'}
          </p>
          {!data && !loading && (
            <button
              onClick={() => localAccountId && fetchServices(localAccountId)}
              className="mt-6 px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:opacity-90"
            >
              Discover Services
            </button>
          )}
        </div>
      )}

      {/* Details Modal */}
      {modalOpen && selectedService && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="max-w-4xl w-full max-h-[90vh] overflow-hidden">
            <div className="p-6 border-b border-border flex justify-between items-center">
              <div>
                <h3 className="text-xl font-bold text-foreground">
                  {selectedService.service_info?.name || 'Unknown Service'}
                </h3>
                <p className="text-sm text-muted-foreground">{selectedService.category || 'Uncategorized'}</p>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="p-2 hover:bg-muted rounded-lg"
                title="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
              <div className="space-y-4">
                {(selectedService.resources || [])
                  .filter(r => r && typeof r.estimated_monthly_cost === 'number' && !isNaN(r.estimated_monthly_cost))
                  .sort((a, b) => (b.estimated_monthly_cost || 0) - (a.estimated_monthly_cost || 0))
                  .map((resource, idx) => (
                    <Card key={idx} className="p-4">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <p className="font-semibold text-foreground">
                              {resource.resource_name || 'Unnamed Resource'}
                            </p>
                            <span className="text-xs px-2 py-1 bg-primary/10 text-primary rounded">
                              {resource.region || 'Unknown'}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground font-mono mb-3">
                            {resource.resource_id || 'No ID'}
                          </p>
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div>
                              <span className="text-muted-foreground">Count:</span>
                              <span className="ml-2 font-medium">{resource.count || 1}</span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Monthly Cost:</span>
                              <span className="ml-2 font-bold text-primary">
                                ${(resource.estimated_monthly_cost || 0).toFixed(2)}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </Card>
                  ))}
              </div>
            </div>
            
            <div className="p-6 border-t border-border bg-muted/30">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-sm text-muted-foreground">Total Monthly Cost</p>
                  <p className="text-2xl font-bold text-foreground">
                    ${(selectedService.total_monthly_cost || 0).toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Resources</p>
                  <p className="text-2xl font-bold text-foreground">
                    {selectedService.total_count || 0}
                  </p>
                </div>
                <button
                  onClick={() => setModalOpen(false)}
                  className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90"
                >
                  Close
                </button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </Card>
  );
};

export default CostAnalyticsProvider;