export interface User {
  id: string;
  email: string;
  full_name: string;
  org_id: string;
  role: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  company_profile: string | null;
  capability_statement: string | null;
  created_at: string;
}

export interface RequirementItem {
  id: string;
  section: string;
  requirement_text: string;
  priority: "must" | "should" | "informational";
  source_reference: string;
}

export interface ComplianceRow {
  requirement_id: string;
  status: "met" | "partial" | "missing";
  evidence: string;
  owner: string | null;
  notes: string;
}

export interface ExtractedSection {
  section_id: string;
  section_title: string;
  subsections: string[];
  requirements: string[];
  page_limit: number | null;
  is_mandatory: boolean;
  evaluation_weight: string | null;
  order: number;
}

export interface Project {
  id: string;
  title: string;
  status: string;
  rfp_type: string | null;
  metadata_json: Record<string, string>;
  detected_sections: ExtractedSection[];
  requirements: RequirementItem[];
  compliance_matrix: ComplianceRow[];
  gaps: string[];
  draft_sections: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface ProjectListItem {
  id: string;
  title: string;
  status: string;
  rfp_type: string | null;
  metadata_json: Record<string, string>;
  created_at: string;
}

export interface Conversation {
  id: string;
  project_id: string;
  title: string | null;
  section_key: string | null;
  created_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface Member {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}
