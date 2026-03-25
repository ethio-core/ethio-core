'use client'

import { useCallback, useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { formatDateTime, getSeverityColor } from '@/lib/utils'
import { Shield, AlertTriangle, CheckCircle, XCircle, Eye, RefreshCw, Loader2 } from 'lucide-react'
import api, { type IntegrityReport, type SecurityAlert } from '@/services/api'

export default function SecurityPage() {
  const [alerts, setAlerts] = useState<SecurityAlert[]>([])
  const [integrityReport, setIntegrityReport] = useState<IntegrityReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [checking, setChecking] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    const res = await api.getSecurityAlerts({ limit: 200 })
    if (res.data) setAlerts(res.data.items)
    setLoading(false)
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const runIntegrity = async () => {
    setChecking(true)
    const res = await api.verifyIntegrity()
    setChecking(false)
    if (res.data) setIntegrityReport(res.data)
    else alert(res.error || 'Integrity check failed')
  }

  const resolve = async (id: string) => {
    const res = await api.resolveSecurityAlert(id)
    if (res.error) alert(res.error)
    load()
  }

  const unresolvedAlerts = alerts.filter((a) => !a.resolved)
  const criticalAlerts = alerts.filter((a) => a.severity === 'critical')

  const integrityStatus = integrityReport
    ? {
        lastCheck: integrityReport.checked_at,
        status: integrityReport.status,
        recordsChecked: integrityReport.records_checked,
        invalidRecords: integrityReport.invalid_records.length,
      }
    : {
        lastCheck: '',
        status: 'unknown',
        recordsChecked: 0,
        invalidRecords: 0,
      }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Security Center</h2>
          <p className="text-sm text-muted-foreground">Monitor security alerts and system integrity</p>
        </div>
        <Button onClick={runIntegrity} disabled={checking}>
          {checking ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
          Run Integrity Check
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-yellow-100">
                <AlertTriangle className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{unresolvedAlerts.length}</p>
                <p className="text-sm text-muted-foreground">Unresolved Alerts</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-red-200">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                <XCircle className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-red-600">{criticalAlerts.length}</p>
                <p className="text-sm text-muted-foreground">Critical Alerts</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                <Shield className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-green-600">
                  {integrityReport?.status === 'valid' ? 'Valid' : integrityReport ? 'Invalid' : '—'}
                </p>
                <p className="text-sm text-muted-foreground">System Integrity</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
                <CheckCircle className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {integrityReport ? integrityReport.records_checked.toLocaleString() : '—'}
                </p>
                <p className="text-sm text-muted-foreground">Records Verified</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Audit Log Integrity Report
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg bg-muted p-4">
              <p className="text-sm text-muted-foreground">Last Check</p>
              <p className="font-medium">
                {integrityStatus.lastCheck ? formatDateTime(integrityStatus.lastCheck) : 'Not run yet'}
              </p>
            </div>
            <div className="rounded-lg bg-muted p-4">
              <p className="text-sm text-muted-foreground">Status</p>
              <p className="font-medium text-green-600">
                {integrityStatus.status === 'valid'
                  ? 'All Records Valid'
                  : integrityStatus.status === 'invalid'
                    ? 'Issues Found'
                    : '—'}
              </p>
            </div>
            <div className="rounded-lg bg-muted p-4">
              <p className="text-sm text-muted-foreground">Records Checked</p>
              <p className="font-medium">{integrityStatus.recordsChecked.toLocaleString()}</p>
            </div>
            <div className="rounded-lg bg-muted p-4">
              <p className="text-sm text-muted-foreground">Invalid Records</p>
              <p className="font-medium">{integrityStatus.invalidRecords}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Security Alerts
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground py-8 text-center">Loading…</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Message</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alerts.map((alert) => (
                  <TableRow key={alert.id}>
                    <TableCell className="font-medium">{alert.type}</TableCell>
                    <TableCell>
                      <Badge className={getSeverityColor(alert.severity)} variant="outline">
                        {alert.severity}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-[300px]">{alert.message}</TableCell>
                    <TableCell>
                      {alert.resolved ? (
                        <Badge variant="outline" className="bg-green-100 text-green-800">
                          Resolved
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="bg-yellow-100 text-yellow-800">
                          Open
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>{formatDateTime(alert.created_at)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="ghost" size="icon">
                          <Eye className="h-4 w-4" />
                        </Button>
                        {!alert.resolved && (
                          <Button variant="ghost" size="sm" onClick={() => resolve(alert.id)}>
                            Resolve
                          </Button>
                        )}
                      </div>
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
