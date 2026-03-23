"use client"

import { useState } from "react"
import Link from "next/link"
import { Menu, X, CreditCard, Shield, Fingerprint, Globe, ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const navItems = [
  { label: "Overview", href: "#overview" },
  { label: "Architecture", href: "#architecture" },
  { label: "Security", href: "#security" },
  { label: "AI & Biometrics", href: "#ai-biometrics" },
  { label: "Features", href: "#features" },
  { label: "Implementation", href: "#implementation" },
]

export function Navigation() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl">
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 lg:px-8">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
            <CreditCard className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="text-xl font-bold text-foreground">AfriCard</span>
        </Link>

        {/* Desktop Navigation */}
        <div className="hidden items-center gap-1 md:flex">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
            >
              {item.label}
            </Link>
          ))}
        </div>

        <div className="hidden items-center gap-3 md:flex">
          <Button variant="ghost" size="sm">
            Documentation
          </Button>
          <Link href="/demo">
            <Button size="sm">
              Try Demo
            </Button>
          </Link>
        </div>

        {/* Mobile Menu Button */}
        <button
          className="md:hidden"
          onClick={() => setIsOpen(!isOpen)}
          aria-label="Toggle menu"
        >
          {isOpen ? (
            <X className="h-6 w-6 text-foreground" />
          ) : (
            <Menu className="h-6 w-6 text-foreground" />
          )}
        </button>
      </nav>

      {/* Mobile Navigation */}
      {isOpen && (
        <div className="border-t border-border bg-background md:hidden">
          <div className="space-y-1 px-4 py-4">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block rounded-md px-3 py-2 text-base font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                onClick={() => setIsOpen(false)}
              >
                {item.label}
              </Link>
            ))}
            <div className="mt-4 flex flex-col gap-2 pt-4 border-t border-border">
              <Button variant="ghost" className="justify-start">
                Documentation
              </Button>
              <Link href="/demo" onClick={() => setIsOpen(false)}>
                <Button className="w-full justify-start">
                  Try Demo
                </Button>
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  )
}
