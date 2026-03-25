'use client'

import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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
import { formatCurrency, formatDateTime, getStatusColor } from '@/lib/utils'
import { Search, ArrowUpRight, ArrowDownLeft, RefreshCw, Eye, Loader2 } from 'lucide-react'
import api, { type Customer, type Transaction } from '@/services/api'

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [showTransfer, setShowTransfer] = useState(false)
  const [saving, setSaving] = useState(false)
  const [transfer, setTransfer] = useState({
    from_customer_id: '',
    to_customer_id: '',
    amount: '1000',
    description: '',
  })

  const load = useCallback(async () => {
    setLoading(true)
    const [txRes, custRes] = await Promise.all([
      api.getTransactions({ limit: 200 }),
      api.getCustomers({ limit: 200 }),
    ])
    if (txRes.data) setTransactions(txRes.data.items)
    if (custRes.data) setCustomers(custRes.data.items)
    setLoading(false)
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const filteredTransactions = transactions.filter((txn) => {
    const name = txn.customer_name || ''
    const matchesSearch =
      name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      txn.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      txn.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = filterStatus === 'all' || txn.status === filterStatus
    return matchesSearch && matchesStatus
  })

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'credit':
        return <ArrowDownLeft className="h-4 w-4 text-green-600" />
      case 'debit':
        return <ArrowUpRight className="h-4 w-4 text-red-600" />
      case 'transfer':
        return <RefreshCw className="h-4 w-4 text-blue-600" />
      default:
        return null
    }
  }

  const stats = {
    total: transactions.length,
    volume: transactions.filter((t) => t.status === 'completed').reduce((sum, t) => sum + t.amount, 0),
    pending: transactions.filter((t) => t.status === 'pending').length,
    failed: transactions.filter((t) => t.status === 'failed').length,
  }

  const submitTransfer = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    const res = await api.initiateTransfer({
      from_customer_id: transfer.from_customer_id,
      to_customer_id: transfer.to_customer_id,
      amount: parseFloat(transfer.amount),
      currency: 'ETB',
      description: transfer.description || undefined,
    })
    setSaving(false)
    if (res.data) {
      setShowTransfer(false)
      load()
    } else {
      alert(res.error || 'Transfer failed')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Transaction History</h2>
          <p className="text-sm text-muted-foreground">View and manage all transactions</p>
        </div>
        <Button onClick={() => setShowTransfer(!showTransfer)}>
          <RefreshCw className="mr-2 h-4 w-4" />
          New Transfer
        </Button>
      </div>

      {showTransfer && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Transfer (MVP ledger)</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={submitTransfer} className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-2">
                <Label>From customer</Label>
                <select
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={transfer.from_customer_id}
                  onChange={(e) => setTransfer((t) => ({ ...t, from_customer_id: e.target.value }))}
                  required
                >
                  <option value="">Select…</option>
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.first_name} {c.last_name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label>To customer</Label>
                <select
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={transfer.to_customer_id}
                  onChange={(e) => setTransfer((t) => ({ ...t, to_customer_id: e.target.value }))}
                  required
                >
                  <option value="">Select…</option>
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.first_name} {c.last_name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label>Amount (ETB)</Label>
                <Input
                  type="number"
                  min={1}
                  step="0.01"
                  value={transfer.amount}
                  onChange={(e) => setTransfer((t) => ({ ...t, amount: e.target.value }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Input
                  value={transfer.description}
                  onChange={(e) => setTransfer((t) => ({ ...t, description: e.target.value }))}
                />
              </div>
              <div className="flex items-end gap-2 md:col-span-2">
                <Button type="submit" disabled={saving}>
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Submit transfer'}
                </Button>
                <Button type="button" variant="outline" onClick={() => setShowTransfer(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-2xl font-bold">{stats.total}</p>
            <p className="text-sm text-muted-foreground">Total Transactions</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-2xl font-bold">{formatCurrency(stats.volume)}</p>
            <p className="text-sm text-muted-foreground">Completed Volume</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-2xl font-bold text-yellow-600">{stats.pending}</p>
            <p className="text-sm text-muted-foreground">Pending</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-2xl font-bold text-red-600">{stats.failed}</p>
            <p className="text-sm text-muted-foreground">Failed</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle>All Transactions</CardTitle>
            <div className="flex gap-2">
              <div className="relative w-full sm:w-64">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search transactions..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="rounded-md border bg-background px-3 py-2 text-sm"
              >
                <option value="all">All Status</option>
                <option value="completed">Completed</option>
                <option value="pending">Pending</option>
                <option value="failed">Failed</option>
                <option value="reversed">Reversed</option>
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
                  <TableHead>Transaction ID</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTransactions.map((txn) => (
                  <TableRow key={txn.id}>
                    <TableCell className="font-mono text-sm">{txn.id.slice(0, 8)}…</TableCell>
                    <TableCell className="font-medium">{txn.customer_name || txn.customer_id}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {getTypeIcon(txn.type)}
                        <span className="capitalize">{txn.type}</span>
                      </div>
                    </TableCell>
                    <TableCell
                      className={txn.type === 'credit' ? 'text-green-600' : 'text-foreground'}
                    >
                      {txn.type === 'credit' ? '+' : '-'}
                      {formatCurrency(txn.amount, txn.currency)}
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(txn.status)} variant="outline">
                        {txn.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate">{txn.description}</TableCell>
                    <TableCell>{formatDateTime(txn.created_at)}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon">
                        <Eye className="h-4 w-4" />
                      </Button>
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
