"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import type { Member, Organization } from "@/types";
import { useQuery, useQueryClient } from "@tanstack/react-query";

export default function SettingsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const isAdmin = user?.role === "owner" || user?.role === "admin";

  const { data: org } = useQuery<Organization>({
    queryKey: ["org"],
    queryFn: () => api.get("/api/v1/org"),
  });

  const { data: members } = useQuery<Member[]>({
    queryKey: ["members"],
    queryFn: () => api.get("/api/v1/org/members"),
  });

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteMsg, setInviteMsg] = useState("");
  const [companyProfile, setCompanyProfile] = useState("");
  const [profileSaved, setProfileSaved] = useState(false);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const invite = await api.post<{ token: string }>("/api/v1/org/invites", {
        email: inviteEmail,
        role: "member",
      });
      setInviteMsg(`Invite link: ${window.location.origin}/invite/${invite.token}`);
      setInviteEmail("");
      queryClient.invalidateQueries({ queryKey: ["members"] });
    } catch (err: any) {
      setInviteMsg(`Error: ${err.message}`);
    }
  };

  const handleSaveProfile = async () => {
    try {
      await api.patch("/api/v1/org", { company_profile: companyProfile });
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 3000);
    } catch {}
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      {/* Org profile */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Organization Profile</h2>
        <p className="text-sm text-gray-500 mb-3">
          This default company profile is used when analyzing new RFPs.
        </p>
        <textarea
          rows={6}
          value={companyProfile || org?.company_profile || ""}
          onChange={(e) => setCompanyProfile(e.target.value)}
          className="input-field mb-3"
          placeholder="Describe your company..."
          disabled={!isAdmin}
        />
        {isAdmin && (
          <button onClick={handleSaveProfile} className="btn-primary">
            {profileSaved ? "Saved!" : "Save Profile"}
          </button>
        )}
      </div>

      {/* Team */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Team Members</h2>
        <div className="space-y-3 mb-6">
          {members?.map((m) => (
            <div key={m.id} className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">{m.full_name}</p>
                <p className="text-xs text-gray-500">{m.email}</p>
              </div>
              <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                {m.role}
              </span>
            </div>
          ))}
        </div>

        {isAdmin && (
          <>
            <h3 className="text-sm font-medium text-gray-700 mb-2">Invite Team Member</h3>
            <form onSubmit={handleInvite} className="flex gap-2">
              <input
                type="email"
                required
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                className="input-field flex-1"
                placeholder="colleague@company.com"
              />
              <button type="submit" className="btn-primary">
                Invite
              </button>
            </form>
            {inviteMsg && (
              <p className="mt-2 text-sm text-gray-600 break-all">{inviteMsg}</p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
