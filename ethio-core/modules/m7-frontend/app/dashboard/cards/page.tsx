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
import { formatDate, getStatusColor, maskCardNumber } from '@/lib/utils'
import { Plus, Search, CreditCard, Lock, Unlock, Eye, Loader2 } from 'lucide-react'
import api, { type Card, type Customer } from '@/services/api'

export default function CardsPage() {
  const [cards, setCards] = useState<Card[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [showIssue, setShowIssue] = useState(false)
  const [saving, setSaving] = useState(false)
  const [issue, setIssue] = useState<{ customer_id: string; card_type: 'virtual' | 'physical' }>({
    customer_id: '',
    card_type: 'virtual',
  })

  const load = useCallback(async () => {
    setLoading(true)
    const [cRes, cuRes] = await Promise.all([
      api.getCards(),
      api.getCustomers({ limit: 200 }),
    ])
    if (cRes.data) setCards(cRes.data.items)
    if (cuRes.data) setCustomers(cuRes.data.items)
    setLoading(false)
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const filteredCards = cards.filter(
    (card) =>
      (card.customer_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      card.card_number_masked.includes(searchQuery)
  )

  const stats = {
    total: cards.length,
    active: cards.filter((c) => c.status === 'active').length,
    blocked: cards.filter((c) => c.status === 'blocked').length,
    virtual: cards.filter((c) => c.card_type === 'virtual').length,
  }

  const issueCard = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!issue.customer_id) return
    setSaving(true)
    const res = await api.requestCard({ customer_id: issue.customer_id, card_type: issue.card_type })
    setSaving(false)
    if (res.data) {
      setShowIssue(false)
      load()
    } else {
      alert(res.error || 'Failed to issue card')
    }
  }

  const toggleBlock = async (card: Card) => {
    if (card.status === 'active') {
      const res = await api.blockCard(card.id, 'Operator hold')
      if (res.error) alert(res.error)
    } else if (card.status === 'blocked') {
      const res = await api.activateCard(card.id)
      if (res.error) alert(res.error)
    }
    load()
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Card Management</h2>
          <p className="text-sm text-muted-foreground">Issue and manage customer cards</p>
        </div>
        <Button onClick={() => setShowIssue(!showIssue)}>
          <Plus className="mr-2 h-4 w-4" />
          Issue New Card
        </Button>
      </div>

      {showIssue && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Issue card</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={issueCard} className="flex flex-wrap items-end gap-4">
              <div className="space-y-2 min-w-[200px]">
                <Label>Customer</Label>
                <select
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={issue.customer_id}
                  onChange={(e) => setIssue((i) => ({ ...i, customer_id: e.target.value }))}
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
                <Label>Type</Label>
                <select
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={issue.card_type}
                  onChange={(e) =>
                    setIssue((i) => ({ ...i, card_type: e.target.value as 'virtual' | 'physical' }))
                  }
                >
                  <option value="virtual">virtual</option>
                  <option value="physical">physical</option>
                </select>
              </div>
              <Button type="submit" disabled={saving}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Create'}
              </Button>
              <Button type="button" variant="outline" onClick={() => setShowIssue(false)}>
                Cancel
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                <CreditCard className="h-6 w-6 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.total}</p>
                <p className="text-sm text-muted-foreground">Total Cards</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                <CreditCard className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.active}</p>
                <p className="text-sm text-muted-foreground">Active</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                <Lock className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.blocked}</p>
                <p className="text-sm text-muted-foreground">Blocked</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
                <CreditCard className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.virtual}</p>
                <p className="text-sm text-muted-foreground">Virtual Cards</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle>All Cards</CardTitle>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search cards..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
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
                  <TableHead>Customer</TableHead>
                  <TableHead>Card Number</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Expiry</TableHead>
                  <TableHead>Issued</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredCards.map((card) => (
                  <TableRow key={card.id}>
                    <TableCell className="font-medium">
                      {card.customer_name || card.customer_id}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {maskCardNumber(card.card_number_masked)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">
                        {card.card_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(card.status)} variant="outline">
                        {card.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{card.expiry_date}</TableCell>
                    <TableCell>{formatDate(card.created_at)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="ghost" size="icon" title="View Details">
                          <Eye className="h-4 w-4" />
                        </Button>
                        {card.status === 'active' ? (
                          <Button variant="ghost" size="icon" title="Block Card" onClick={() => toggleBlock(card)}>
                            <Lock className="h-4 w-4" />
                          </Button>
                        ) : card.status === 'blocked' ? (
                          <Button variant="ghost" size="icon" title="Activate Card" onClick={() => toggleBlock(card)}>
                            <Unlock className="h-4 w-4" />
                          </Button>
                        ) : card.status === 'pending' ? (
                          <Button variant="outline" size="sm" onClick={async () => { await api.activateCard(card.id); load() }}>
                            Activate
                          </Button>
                        ) : null}
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
