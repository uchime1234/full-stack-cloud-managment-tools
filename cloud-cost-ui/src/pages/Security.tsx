"use client"

import type React from "react"
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { DashboardLayout } from "../components/layout/DashboardLayout"
import { Card } from "../components/ui/Card"
import { Shield, AlertTriangle, CheckCircle, Lock, Key, Globe, Database, Clock } from "lucide-react"
import type { CloudProvider } from "../types"

const providers: Array<{ id: CloudProvider; name: string; icon: string }> = [
  { id: "aws", name: "AWS", icon: "☁️" },
  { id: "azure", name: "Azure", icon: "⚡" },
  { id: "gcp", name: "GCP", icon: "🔷" },
]

const securityChecks = [
  {
    category: "IAM Security",
    icon: <Key className="w-5 h-5" />,
    issues: [
      { severity: "high", title: "Root account without MFA", resource: "AWS Account", recommendation: "Enable MFA" },
      {
        severity: "medium",
        title: "IAM users with old access keys",
        resource: "3 users",
        recommendation: "Rotate keys",
      },
    ],
  },
  {
    category: "Public Resources",
    icon: <Globe className="w-5 h-5" />,
    issues: [
      {
        severity: "high",
        title: "S3 bucket publicly accessible",
        resource: "app-logs",
        recommendation: "Restrict access",
      },
      {
        severity: "medium",
        title: "Security group allows 0.0.0.0/0",
        resource: "sg-web-public",
        recommendation: "Limit IP ranges",
      },
    ],
  },
  {
    category: "Encryption",
    icon: <Lock className="w-5 h-5" />,
    issues: [
      {
        severity: "low",
        title: "EBS volume not encrypted",
        resource: "vol-data-01",
        recommendation: "Enable encryption",
      },
      {
        severity: "high",
        title: "RDS instance without encryption",
        resource: "db-legacy",
        recommendation: "Migrate to encrypted",
      },
    ],
  },
  {
    category: "Backup Status",
    icon: <Database className="w-5 h-5" />,
    issues: [
      {
        severity: "medium",
        title: "No backup configured",
        resource: "EC2 i-prod-01",
        recommendation: "Enable AWS Backup",
      },
    ],
  },
  {
    category: "Access Key Age",
    icon: <Clock className="w-5 h-5" />,
    issues: [
      {
        severity: "medium",
        title: "Access keys older than 90 days",
        resource: "2 keys",
        recommendation: "Rotate immediately",
      },
    ],
  },
]

export const Security: React.FC = () => {
  const navigate = useNavigate()
  const [selectedProvider, setSelectedProvider] = useState<CloudProvider>("aws")

  const totalIssues = securityChecks.reduce((sum, cat) => sum + cat.issues.length, 0)
  const highSeverity = securityChecks.reduce(
    (sum, cat) => sum + cat.issues.filter((i) => i.severity === "high").length,
    0,
  )
  const mediumSeverity = securityChecks.reduce(
    (sum, cat) => sum + cat.issues.filter((i) => i.severity === "medium").length,
    0,
  )
  const lowSeverity = securityChecks.reduce(
    (sum, cat) => sum + cat.issues.filter((i) => i.severity === "low").length,
    0,
  )

  return (
    <DashboardLayout>
      <div className="p-8 max-w-7xl mx-auto space-y-6">
        <div>
          <button
            onClick={() => navigate("/dashboard")}
            className="text-sm text-muted-foreground hover:text-foreground mb-2 transition-colors"
          >
            ← Back to Dashboard
          </button>
          <h1 className="text-3xl font-bold text-foreground">Cloud Security & Compliance</h1>
          <p className="text-muted-foreground">Security scanning and compliance monitoring</p>
        </div>

        {/* Provider Selection */}
        <div className="flex gap-3">
          {providers.map((provider) => (
            <button
              key={provider.id}
              onClick={() => setSelectedProvider(provider.id)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
                selectedProvider === provider.id
                  ? "bg-primary text-primary-foreground"
                  : "bg-card border border-border text-foreground hover:bg-muted"
              }`}
            >
              <span className="text-xl">{provider.icon}</span>
              {provider.name}
            </button>
          ))}
        </div>

        {/* Overview Stats */}
        <div className="grid grid-cols-4 gap-4">
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Total Issues</p>
                <p className="text-2xl font-bold text-foreground">{totalIssues}</p>
              </div>
              <Shield className="w-8 h-8 text-muted-foreground" />
            </div>
          </Card>
          <Card className="border-l-4 border-l-error">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground mb-1">High Severity</p>
                <p className="text-2xl font-bold text-error">{highSeverity}</p>
              </div>
              <AlertTriangle className="w-8 h-8 text-error" />
            </div>
          </Card>
          <Card className="border-l-4 border-l-warning">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Medium Severity</p>
                <p className="text-2xl font-bold text-warning">{mediumSeverity}</p>
              </div>
              <AlertTriangle className="w-8 h-8 text-warning" />
            </div>
          </Card>
          <Card className="border-l-4 border-l-success">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Low Severity</p>
                <p className="text-2xl font-bold text-success">{lowSeverity}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-success" />
            </div>
          </Card>
        </div>

        {/* Security Checks */}
        <div className="space-y-6">
          {securityChecks.map((check, idx) => (
            <Card key={idx}>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">{check.icon}</div>
                <h3 className="text-lg font-semibold text-foreground">{check.category}</h3>
              </div>

              <div className="space-y-3">
                {check.issues.map((issue, i) => (
                  <div
                    key={i}
                    className={`p-4 rounded-lg border-l-4 ${
                      issue.severity === "high"
                        ? "bg-error/5 border-l-error"
                        : issue.severity === "medium"
                          ? "bg-warning/5 border-l-warning"
                          : "bg-success/5 border-l-success"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${
                              issue.severity === "high"
                                ? "bg-error/20 text-error"
                                : issue.severity === "medium"
                                  ? "bg-warning/20 text-warning"
                                  : "bg-success/20 text-success"
                            }`}
                          >
                            {issue.severity}
                          </span>
                          <h4 className="font-medium text-foreground">{issue.title}</h4>
                        </div>
                        <p className="text-sm text-muted-foreground mb-2">Resource: {issue.resource}</p>
                        <p className="text-sm text-foreground">
                          <strong>Recommendation:</strong> {issue.recommendation}
                        </p>
                      </div>
                      <button className="px-4 py-2 bg-primary text-primary-foreground text-sm rounded-lg hover:opacity-90 transition-all">
                        Fix Now
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      </div>
    </DashboardLayout>
  )
}
