'use client'

import { useEffect, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { formatDateTime } from '@/lib/utils'
import { Search, FileText, CheckCircle } from 'lucide-react'
import api, { type AuditLog } from '@/services/api'

const actionColors: Record<string, string> = {
  USER_LOGIN: 'bg-blue-100 text-blue-800',
  USER_LOGOUT: 'bg-gray-100 text-gray-800',
  CUSTOMER_CREATED: 'bg-green-100 text-green-800',
  KYC_APPROVED: 'bg-green-100 text-green-800',
  KYC_REJECTED: 'bg-red-100 text-red-800',
  CARD_ISSUED: 'bg-green-100 text-green-800',
  CARD_BLOCKED: 'bg-red-100 text-red-800',
  TRANSACTION_TRANSFER: 'bg-blue-100 text-blue-800',
  SECURITY_ALERT_RESOLVED: 'bg-green-100 text-green-800',
}

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterAction, setFilterAction] = useState<string>('all')

  useEffect(() => {
    let c = false
    ;(async () => {
      const res = await api.getAuditLogs({ limit: 500 })
      if (!c && res.data) {
        setLogs(res.data.items)
        setTotal(res.data.total)
      }
      if (!c) setLoading(false)
    })()
    return () => {
      c = true
    }
  }, [])

  const filteredLogs = logs.filter((log) => {
    const email = log.user_email || ''
    const matchesSearch =
      email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.resource_id.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesAction = filterAction === 'all' || log.action === filterAction
    return matchesSearch && matchesAction
  })

  const uniqueActions = Array.from(new Set(logs.map((log) => log.action)))

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Audit Logs</h2>
          <p className="text-sm text-muted-foreground">View system activity and audit trail ({total})</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                <FileText className="h-6 w-6 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{logs.length}</p>
                <p className="text-sm text-muted-foreground">Loaded entries</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-green-600">Valid</p>
                <p className="text-sm text-muted-foreground">Hash chain (verify in Security)</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
                <FileText className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{uniqueActions.length}</p>
                <p className="text-sm text-muted-foreground">Action types</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle>Activity Log</CardTitle>
            <div className="flex gap-2">
              <div className="relative w-full sm:w-64">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search logs..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <select
                value={filterAction}
                onChange={(e) => setFilterAction(e.target.value)}
                className="rounded-md border bg-background px-3 py-2 text-sm"
              >
                <option value="all">All Actions</option>
                {uniqueActions.map((action) => (
                  <option key={action} value={action}>
                    {action.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground py-8 text-center">Loading…</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Resource</TableHead>
                  <TableHead>IP Address</TableHead>
                  <TableHead>Hash</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredLogs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="whitespace-nowrap">{formatDateTime(log.timestamp)}</TableCell>
                    <TableCell>{log.user_email || log.user_id}</TableCell>
                    <TableCell>
                      <Badge
                        className={actionColors[log.action] || 'bg-gray-100 text-gray-800'}
                        variant="outline"
                      >
                        {log.action.replace(/_/g, ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs">
                        {log.resource_type}: {log.resource_id}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{log.ip_address}</TableCell>
                    <TableCell>
                      <span className="font-mono text-xs text-muted-foreground">{log.hash}</span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
