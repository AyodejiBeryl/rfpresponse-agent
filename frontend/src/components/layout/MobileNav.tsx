"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <div className="lg:hidden">
      <div className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-4">
        <h1 className="text-lg font-bold text-primary-600">RFP Platform</h1>
        <button
          onClick={() => setOpen(!open)}
          className="rounded-lg p-2 text-gray-600 hover:bg-gray-100"
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            {open ? (
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            )}
          </svg>
        </button>
      </div>

      {open && (
        <div className="border-b border-gray-200 bg-white px-4 py-3 space-y-1">
          <Link
            href="/projects"
            onClick={() => setOpen(false)}
            className={cn(
              "block rounded-lg px-3 py-2 text-sm font-medium",
              pathname.startsWith("/projects")
                ? "bg-primary-50 text-primary-700"
                : "text-gray-700"
            )}
          >
            Projects
          </Link>
          <Link
            href="/knowledge"
            onClick={() => setOpen(false)}
            className={cn(
              "block rounded-lg px-3 py-2 text-sm font-medium",
              pathname.startsWith("/knowledge")
                ? "bg-primary-50 text-primary-700"
                : "text-gray-700"
            )}
          >
            Knowledge Base
          </Link>
          <Link
            href="/settings"
            onClick={() => setOpen(false)}
            className={cn(
              "block rounded-lg px-3 py-2 text-sm font-medium",
              pathname.startsWith("/settings")
                ? "bg-primary-50 text-primary-700"
                : "text-gray-700"
            )}
          >
            Settings
          </Link>
          <div className="border-t border-gray-200 pt-2 mt-2">
            <p className="px-3 text-sm text-gray-500">{user?.full_name}</p>
            <button
              onClick={() => { logout(); setOpen(false); }}
              className="w-full text-left px-3 py-2 text-sm text-gray-500 hover:text-gray-700"
            >
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
