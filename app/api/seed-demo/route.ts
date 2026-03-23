import { NextResponse } from 'next/server';
import { db, seedDemoData } from '@/lib/database';

export async function POST() {
  const accounts = seedDemoData();
  return NextResponse.json(
    {
      success: true,
      message: 'Demo data seeded',
      accounts,
      stats: db.getStats(),
    },
    { status: 200 },
  );
}

export async function GET() {
  // Allow GET for quick manual testing.
  const accounts = seedDemoData();
  return NextResponse.json(
    {
      success: true,
      message: 'Demo data seeded',
      accounts,
      stats: db.getStats(),
    },
    { status: 200 },
  );
}

