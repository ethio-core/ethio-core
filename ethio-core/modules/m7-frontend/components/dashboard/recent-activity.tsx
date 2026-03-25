import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatDateTime, getStatusColor } from '@/lib/utils'

interface Activity {
  id: string
  type: string
  description: string
  status: string
  timestamp: string
}

interface RecentActivityProps {
  activities: Activity[]
}

export function RecentActivity({ activities }: RecentActivityProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {activities.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No recent activity
            </p>
          ) : (
            activities.map((activity) => (
              <div
                key={activity.id}
                className="flex items-center justify-between border-b pb-4 last:border-0 last:pb-0"
              >
                <div className="space-y-1">
                  <p className="text-sm font-medium">{activity.type}</p>
                  <p className="text-xs text-muted-foreground">{activity.description}</p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <Badge className={getStatusColor(activity.status)} variant="outline">
                    {activity.status}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {formatDateTime(activity.timestamp)}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}
