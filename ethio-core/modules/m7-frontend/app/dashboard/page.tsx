'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { StatsCard } from '@/components/dashboard/stats-card'
import { RecentActivity } from '@/components/dashboard/recent-activity'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Users, CreditCard, ArrowLeftRight, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import { formatCurrency } from '@/lib/utils'
import api, { type DashboardStats } from '@/services/api'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts'

const defaultStats: DashboardStats = {
  total_customers: 0,
  active_cards: 0,
  transactions_today: 0,
  transaction_volume_today: 0,
  pending_kyc: 0,
  security_alerts: 0,
  growth_rates: { customers: 0, transactions: 0 },
  chart_transactions_week: [],
  chart_volume_months: [],
  recent_activity: [],
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>(defaultStats)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      const res = await api.getDashboardStats()
      if (cancelled) return
      if (res.data) {
        setStats(res.data)
        setError(null)
      } else {
        setError(res.error || 'Failed to load dashboard')
      }
      setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const transactionData =
    stats.chart_transactions_week?.length ? stats.chart_transactions_week : [{ name: '-', transactions: 0 }]
  const volumeData =
    stats.chart_volume_months?.length ? stats.chart_volume_months : [{ name: '-', volume: 0 }]
  const recentActivities = stats.recent_activity ?? []
  const g = stats.growth_rates

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading dashboard…</div>
  }

  if (error) {
    return <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm">{error}</div>
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <StatsCard
          title="Total Customers"
          value={stats.total_customers.toLocaleString()}
          icon={Users}
          trend={{ value: g.customers, isPositive: g.customers >= 0 }}
          description="from last month"
        />
        <StatsCard
          title="Active Cards"
          value={stats.active_cards.toLocaleString()}
          icon={CreditCard}
          trend={{ value: g.transactions, isPositive: true }}
          description="from last month"
        />
        <StatsCard
          title="Transactions Today"
          value={stats.transactions_today.toLocaleString()}
          icon={ArrowLeftRight}
          trend={{ value: g.transactions, isPositive: true }}
          description="from yesterday"
        />
        <StatsCard
          title="Volume Today"
          value={formatCurrency(stats.transaction_volume_today)}
          icon={CheckCircle}
          trend={{ value: g.transactions, isPositive: true }}
          description="from yesterday"
        />
        <StatsCard
          title="Pending KYC"
          value={stats.pending_kyc}
          icon={Clock}
          description="awaiting verification"
        />
        <StatsCard
          title="Security Alerts"
          value={stats.security_alerts}
          icon={AlertTriangle}
          description="requires attention"
          className="border-destructive/50"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Daily Transactions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={transactionData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="name" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                    }}
                  />
                  <Bar dataKey="transactions" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Transaction Volume Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={volumeData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="name" className="text-xs" />
                  <YAxis
                    className="text-xs"
                    tickFormatter={(value) => `${(value / 1_000_000).toFixed(1)}M`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                    }}
                    formatter={(value: number) => [formatCurrency(value), 'Volume']}
                  />
                  <Line
                    type="monotone"
                    dataKey="volume"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    dot={{ fill: 'hsl(var(--primary))' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <RecentActivity activities={recentActivities} />

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2">
              <Link
                href="/dashboard/customers"
                className="flex items-center gap-3 rounded-lg border p-4 text-left hover:bg-accent transition-colors"
              >
                <Users className="h-8 w-8 text-primary" />
                <div>
                  <p className="font-medium">New Customer</p>
                  <p className="text-xs text-muted-foreground">Register customer</p>
                </div>
              </Link>
              <Link
                href="/dashboard/cards"
                className="flex items-center gap-3 rounded-lg border p-4 text-left hover:bg-accent transition-colors"
              >
                <CreditCard className="h-8 w-8 text-primary" />
                <div>
                  <p className="font-medium">Issue Card</p>
                  <p className="text-xs text-muted-foreground">Create new card</p>
                </div>
              </Link>
              <Link
                href="/dashboard/transactions"
                className="flex items-center gap-3 rounded-lg border p-4 text-left hover:bg-accent transition-colors"
              >
                <ArrowLeftRight className="h-8 w-8 text-primary" />
                <div>
                  <p className="font-medium">Transfer</p>
                  <p className="text-xs text-muted-foreground">Initiate transfer</p>
                </div>
              </Link>
              <Link
                href="/dashboard/security"
                className="flex items-center gap-3 rounded-lg border p-4 text-left hover:bg-accent transition-colors"
              >
                <AlertTriangle className="h-8 w-8 text-primary" />
                <div>
                  <p className="font-medium">View Alerts</p>
                  <p className="text-xs text-muted-foreground">Security center</p>
                </div>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
